import os
import sys
import time
import yaml
import getpass
import httpx
from typing import Dict
from capture import ScreenCapturer
from trigger import trigger_agent_with_image, trigger_agent_with_text
from vision import VisionProviderAdapter
from ocr import OCRProcessor


def _cfg(d, *keys, default=None):
    for k in keys:
        if d is None:
            return default
        d = d.get(k)
        if d is None:
            return default
    return d


def setup_windows_ansi():
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


RED_ORANGE = "\033[38;2;255;90;20m"
INDIGO = "\033[38;2;63;0;255m"
RESET = "\033[0m"
SPLIT = 40

BANNER_LINES = [
    r" $$$$$$\  $$$$$$$\  $$$$$$$$\ $$\   $$\ $$\      $$\ $$$$$$$$\ $$$$$$$\  $$\   $$\ $$\   $$\ ",
    r"$$  __$$\ $$  __$$\ $$  _____|$$$\  $$ |$$ | $\  $$ |$$  _____|$$  __$$\ $$ |  $$ |$$ |  $$ |",
    r"$$ /  $$ |$$ |  $$ |$$ |      $$$$\ $$ |$$ |$$$\ $$ |$$ |      $$ |  $$ |$$ |  $$ |$$ |  $$ |",
    r"$$ |  $$ |$$$$$$$  |$$$$$\    $$ $$\$$ |$$ $$ $$\$$ |$$$$$\    $$$$$$$  |$$ |  $$ |$$$$$$$$ |",
    r"$$ |  $$ |$$  ____/ $$  __|   $$ \$$$$ |$$$$  _$$$$ |$$  __|   $$  __$$< $$ |  $$ |$$  __$$ |",
    r"$$ |  $$ |$$ |      $$ |      $$ |\$$$ |$$$  / \$$$ |$$ |      $$ |  $$ |$$ |  $$ |$$ |  $$ |",
    r" $$$$$$  |$$ |      $$$$$$$$\ $$ | \$$ |$$  /   \$$ |$$$$$$$$\ $$ |  $$ |\$$$$$$  |$$ |  $$ |",
    r" \______/ \__|      \________|\__|  \__|\__/     \__|\________|\__|  \__| \______/ \__|  \__|",
]


def colorize_line(line):
    return f"{RED_ORANGE}{line[:SPLIT]}{RESET}{INDIGO}{line[SPLIT:]}{RESET}"


def print_banner():
    setup_windows_ansi()
    print()
    for line in BANNER_LINES:
        print(colorize_line(line))
    print("\n" + " " * 35 + f"{RED_ORANGE}S E T U P{RESET}\n")


def load_config():
    config_path = os.environ.get(
        "OPENWERUH_CONFIG", os.path.expanduser("~/.config/openweruh/weruh.yaml")
    )
    if not os.path.exists(config_path):
        print(f"Config not found at {config_path}.")
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "weruh.example.yaml"
        )
        if not os.path.exists(config_path):
            print("No config file found. Please run setup or copy weruh.example.yaml.")
            sys.exit(1)

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def test_gateway_connection(url, token):
    print("\nTesting Gateway connection...")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with httpx.Client(timeout=5) as client:
            payload = {
                "message": "[WERUH] Connection test",
                "name": "OpenWeruh Setup",
                "channel": "last",
            }
            response = client.post(
                f"{url.rstrip('/')}/hooks/agent", json=payload, headers=headers
            )

            if response.status_code in [401, 403]:
                print(f"  [X] Authentication failed (HTTP {response.status_code}).")
                print(f"      {response.text}")
                print("      Check your hook token!")
                return False
            elif response.status_code == 404:
                print(f"  [X] Webhook endpoint not found (HTTP 404).")
                print("      Check your Gateway URL or ensure 'hooks.enabled' is true.")
                return False
            elif response.status_code == 400:
                text = response.text.lower()
                if "token" in text or "auth" in text or "unauthorized" in text:
                    print(f"  [X] Authentication failed (HTTP 400).")
                    print(f"      {response.text}")
                    return False
                print("  [OK] Gateway connection successful (auth passed).")
                return True
            elif response.status_code == 200:
                print("  [OK] Gateway connection and authentication successful!")
                return True
            else:
                print(f"  [!] Unexpected HTTP {response.status_code}: {response.text}")
                return True
    except httpx.RequestError as e:
        print(f"  [X] Cannot connect to Gateway ({e}).")
        print("      Is OpenClaw running? Is the URL correct?")
        return False


def _section(title):
    print()
    print(f"  \033[36m┌─ {title} {'─' * max(0, 50 - len(title))}─┐\033[0m")


def _choice(prompt, choices, current=None):
    print(f"\n  \033[1m{prompt}\033[0m")
    for i, c in enumerate(choices):
        marker = (
            "\033[32m\u25cf\033[0m"
            if (current is not None and i == current)
            else "\033[90m\u25cb\033[0m"
        )
        num = f"\033[36m{i + 1}\033[0m"
        print(f"    {marker}  {num}) {c}")
    while True:
        try:
            val = input(
                f"    \033[90m(1-{len(choices)}) [{(current + 1) if current is not None else ''}]: \033[0m"
            ).strip()
            if not val:
                return current if current is not None else 0
            n = int(val)
            if 1 <= n <= len(choices):
                return n - 1
            print("    \033[91mInvalid.\033[0m Enter a number.")
        except ValueError:
            print("    \033[91mInvalid.\033[0m Enter a number.")
        except KeyboardInterrupt:
            print("\n\nSetup cancelled.")
            sys.exit(1)
            sys.exit(1)


def _text(prompt, default=""):
    if default:
        val = input(f"  {prompt} \033[90m[default: {default}]: \033[0m").strip()
    else:
        val = input(f"  {prompt}: ").strip()
    return val or default


def _password(prompt, default_masked="***"):
    val = getpass.getpass(f"  {prompt} \033[90m[*** if set]: \033[0m").strip()
    return val or None


def _install_openclaw_components(config: Dict):
    gateway_config = config.get("gateway", {})
    url = gateway_config.get("url", "http://127.0.0.1:18789").rstrip("/")
    token = gateway_config.get("hook_token", "")

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    agent_exec_msg = (
        "[OpenWeruh Setup] Installing OpenWeruh components on this server.\n\n"
        "IMPORTANT: Please execute the following commands using the exec tool IN ORDER:\n\n"
        "1. Clone the repository:\n"
        "   git clone https://github.com/fikriaf/OpenWeruh.git\n\n"
        "2. Install the skill (ClawHub):\n"
        "   npx clawhub install openweruh --no-input\n\n"
        "3. Install the hook (local path):\n"
        "   openclaw hooks install OpenWeruh/hook/weruh-boot\n\n"
        "If clawhub is not installed, run first: npm install -g clawhub\n"
        "After all commands succeed, confirm by running: openclaw hooks list\n"
        "Then restart the gateway: openclaw gateway restart\n\n"
        "Report the output of each command."
    )

    data = {
        "message": agent_exec_msg,
        "name": "OpenWeruh Setup",
        "sessionKey": "hook:weruh:install",
        "deliver": True,
        "wakeMode": "now",
        "channel": "last",
    }

    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(f"{url}/hooks/agent", json=data, headers=headers)
            if response.status_code >= 400:
                return (None, f"Install trigger failed: HTTP {response.status_code}")
            return ("ok", None)
    except httpx.RequestError as e:
        return (None, f"Install webhook failed: {e}")


def _show_install_commands():
    print()
    print("  \033[36m────────────────────────────────────────────\033[0m")
    print("  \033[1m  OpenClaw Component Installation\033[0m")
    print("  \033[36m────────────────────────────────────────────\033[0m")
    print()
    print("  \033[33m!\033[0m  The commands below have been sent to OpenClaw agent.")
    print("  \033[90m  Also paste them manually into OpenClaw (web UI / Telegram)")
    print("  \033[90m  to ensure execution if the agent doesn't respond.\033[0m")
    print()
    print("  Run these commands IN ORDER:")
    print()
    print("  \033[32m1.\033[0m  git clone https://github.com/fikriaf/OpenWeruh.git")
    print()
    print("  \033[32m2.\033[0m  npx clawhub install openweruh --no-input")
    print()
    print("  \033[32m3.\033[0m  openclaw hooks install OpenWeruh/hook/weruh-boot")
    print()
    print(
        "  \033[90m  If clawhub is not found, run first: npm install -g clawhub\033[0m"
    )
    print()
    print("  \033[90m  After all succeed, confirm: openclaw hooks list\033[0m")
    print("  \033[90m  Then restart gateway: openclaw gateway restart\033[0m")
    print()
    print("  \033[90m[Press Enter to continue...]\033[0m")
    input()


def _show_openclaw_setup_commands(token: str):
    print()
    print("  \033[36m────────────────────────────────────────────\033[0m")
    print(
        "  \033[1m  Configure OpenClaw First\033[0m  \033[90m(run where OpenClaw runs)\033[0m"
    )
    print("  \033[36m────────────────────────────────────────────\033[0m")
    print()
    print(
        "  \033[33m!\033[0m  Paste the commands below into OpenClaw (web UI / Telegram)"
    )
    print(
        "  \033[90m  BEFORE continuing. This enables the webhook that OpenWeruh needs.\033[0m"
    )
    print()
    print("  \033[32mRun in OpenClaw terminal (web UI / CLI):\033[0m")
    print()
    print("  \033[36mopenclaw config set hooks.enabled true\033[0m")
    print(f'  \033[36mopenclaw config set hooks.token "{token}"\033[0m')
    print("  \033[36mopenclaw config set hooks.allowRequestSessionKey true\033[0m")
    print()
    print(
        "  \033[90m  After running the commands above, press Enter to continue.\033[0m"
    )
    print("  \033[90m  Or restart OpenClaw gateway first if needed.\033[0m")
    print()
    print("  \033[90m[Press Enter after configuring OpenClaw...]\033[0m")
    input()


def _show_openclaw_notes():
    print()
    print("  \033[36m────────────────────────────────────────────\033[0m")
    print(
        "  \033[1m  OpenClaw Configuration\033[0m  \033[90m(run where OpenClaw runs)\033[0m"
    )
    print("  \033[36m────────────────────────────────────────────\033[0m")
    print()
    print("  \033[33m?\033[0m  Telegram not reaching you?")
    print("     Edit openclaw.json:")
    print('       channels.telegram.allowFrom = ["*"],')
    print('       channels.telegram.dmPolicy = "open"')
    print()
    print("  \033[33m?\033[0m  See \033[91m'unknown entries (image)'\033[0m error?")
    print("     Edit openclaw.json:")
    print('       tools.profile = "minimal"')
    print()
    print("  \033[90m[Press Enter to continue with OpenWeruh setup...]\033[0m")
    input()


def run_setup():
    print_banner()

    config_dir = os.path.expanduser("~/.config/openweruh")
    config_path = os.path.join(config_dir, "weruh.yaml")
    existing = None

    if os.path.exists(config_path):
        print(f"  \033[90mExisting config found at {config_path}")
        print("  Press Enter on each field to keep the current value.\033[0m")
        with open(config_path) as f:
            existing = yaml.safe_load(f)
    else:
        print("  \033[90mNo existing config found. Creating new configuration.\033[0m")

    _section("Gateway")

    modes = [
        "On this same machine (local)",
        "On a remote server (SSH tunnel)",
        "On a remote server (public URL / Tailscale)",
    ]
    mode_labels = ["local", "tunnel", "remote"]
    current_mode = (
        mode_labels.index(existing["gateway"]["mode"])
        if existing and existing.get("gateway", {}).get("mode") in mode_labels
        else None
    )
    gw_idx = _choice(
        "Where is your OpenClaw Gateway running?", modes, current=current_mode
    )
    gw_mode = mode_labels[gw_idx]

    default_url = (
        "http://127.0.0.1:18789" if gw_idx == 0 else ("https://" if gw_idx == 2 else "")
    )
    gw_url = _text(
        f"Gateway URL [{existing['gateway']['url'] if existing and existing.get('gateway', {}).get('url') else default_url}]: ",
        default=existing["gateway"]["url"]
        if existing and existing.get("gateway", {}).get("url")
        else default_url,
    )

    masked = (
        "***...***"
        if existing and existing.get("gateway", {}).get("hook_token")
        else ""
    )
    print(f"  Hook token (from openclaw.json \u2192 hooks.token)")
    print(f"    \033[90m[Enter to keep: {masked}]\033[0m")
    new_token = getpass.getpass("    (leave empty to keep existing): ").strip()
    gw_token = (
        new_token
        if new_token
        else (
            existing["gateway"]["hook_token"]
            if existing and existing.get("gateway", {}).get("hook_token")
            else None
        )
    )
    if not gw_token:
        print("  \033[91m[X] Hook token is required.\033[0m")
        sys.exit(1)

    preflight_config = {
        "gateway": {"mode": gw_mode, "url": gw_url, "hook_token": gw_token}
    }

    _show_openclaw_setup_commands(gw_token)

    config = {
        "gateway": preflight_config["gateway"],
        "persona": {
            "mode": "skeptic",
            "language": "en",
            "tone": "casual",
            "intervention_threshold": "medium",
        },
        "capture": {
            "interval_seconds": 60,
            "change_threshold": 10,
            "active_hours": "07:00-23:00",
            "notify_after_idle_minutes": 5,
        },
    }

    try:
        if not test_gateway_connection(gw_url, gw_token):
            print("\n  Please fix the gateway settings and run setup again.")
            sys.exit(1)

        ok, err = _install_openclaw_components(preflight_config)
        if err:
            print(f"\n  \033[91m[X]\033[0m {err}")
        _show_install_commands()

        _section("Screen Analysis")

        analysis = [
            "OpenClaw has a vision-capable AI model (send image directly \u2014 recommended)",
            "Text-Only Mode: OCR (extract visible TEXT \u2014 no LLM needed)",
            "Text-Only Mode: Vision API (describe screen via LLM)",
        ]

        current_analysis = None
        if existing:
            if _cfg(existing, "ocr", "enabled"):
                current_analysis = 1
            elif _cfg(existing, "vision", "provider", "type"):
                current_analysis = 2
            else:
                current_analysis = 0

        vision_idx = _choice(
            "How should screen content be analyzed?", analysis, current=current_analysis
        )
        config["ocr"] = {"enabled": False}
        config["vision"] = {"provider": {}}

        if vision_idx == 0:
            config["ocr"] = {"enabled": False}
            config["vision"] = {"provider": {}}
            if existing:
                e_ocr = existing.get("ocr")
                e_vision = existing.get("vision")
                if e_ocr:
                    config["ocr"] = e_ocr
                if e_vision:
                    config["vision"] = e_vision
            print("\n  \033[32m[OK]\033[0m OpenClaw will receive raw images.")

        elif vision_idx == 1:
            ocr_libs = [
                "Tesseract OCR (pytesseract) \u2014 fastest",
                "EasyOCR \u2014 better for complex layouts",
            ]
            current_lib = (
                0
                if (existing and _cfg(existing, "ocr", "library") == "pytesseract")
                else 1
                if (existing and _cfg(existing, "ocr", "library") == "easyocr")
                else None
            )
            lib_idx = _choice("Choose an OCR library:", ocr_libs, current=current_lib)
            ocr_lib = "pytesseract" if lib_idx == 0 else "easyocr"

            if ocr_lib == "pytesseract":
                import shutil

                if not shutil.which("tesseract") and not os.path.exists(
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                ):
                    print("\n  \033[91m[X] Tesseract OCR is not installed!\033[0m")
                    print("\n  Install Tesseract OCR first:")
                    print("    Windows: choco install tesseract -y")
                    print(
                        "            OR https://github.com/UB-Mannheim/tesseract/wiki"
                    )
                    print("    macOS:   brew install tesseract")
                    print("    Linux:   sudo apt install tesseract-ocr")
                    print("\n  After installing, run setup again.")
                    sys.exit(1)

            current_lang = (
                _cfg(existing, "ocr", "lang", default="eng+ind")
                if existing
                else "eng+ind"
            )
            lang = _text(f"OCR language codes [{current_lang}]: ", default=current_lang)

            config["ocr"] = {"enabled": True, "library": ocr_lib, "lang": lang}
            print(f"\n  \033[32m[OK]\033[0m OCR Text-Only Mode enabled ({ocr_lib}).")

        elif vision_idx == 2:
            providers = [
                ("ollama", "Ollama (local, full privacy)"),
                ("openai", "OpenAI (GPT-4o)"),
                ("anthropic", "Anthropic (Claude Sonnet)"),
                ("google", "Google (Gemini Flash)"),
                ("openrouter", "OpenRouter (200+ models)"),
                ("mistral", "Mistral (Pixtral)"),
                ("together", "Together AI"),
                ("xai", "xAI (Grok)"),
                ("custom", "Custom / Self-hosted"),
            ]
            p_labels = [p[1] for p in providers]
            current_ptype = (
                next(
                    (
                        i
                        for i, p in enumerate(providers)
                        if p[0] == _cfg(existing, "vision", "provider", "type")
                    ),
                    None,
                )
                if existing
                else None
            )
            p_idx = _choice(
                "Choose a vision provider:", p_labels, current=current_ptype
            )
            ptype = providers[p_idx][0]

            current_model = (
                _cfg(existing, "vision", "provider", "model", default="") or ""
            )
            current_url = _cfg(existing, "vision", "provider", "url", default="") or ""
            current_key = (
                _cfg(existing, "vision", "provider", "api_key", default="") or ""
            )

            model = _text(f"Model name [{current_model}]: ", default=current_model)
            override_url = _text(
                f"Override URL (leave empty for default) [{current_url}]: ",
                default=current_url,
            )
            api_key = ""
            if ptype != "ollama":
                masked_key = "***...***" if current_key else ""
                print(f"  API Key")
                if masked_key:
                    print(f"    \033[90m[Enter to keep: {masked_key}]\033[0m")
                api_key = getpass.getpass("    (leave empty to keep): ").strip()
                if not api_key and current_key:
                    api_key = current_key

            config["vision"]["provider"] = {
                "type": ptype,
                "api_key": api_key,
                "model": model,
                "url": override_url,
            }
            print(f"\n  \033[32m[OK]\033[0m Vision provider configured ({ptype}).")

        if vision_idx in [0, 2]:
            _section("Fallback Vision Provider")

            use_fb = _choice(
                "Add a fallback Vision Provider for when OpenClaw image pipeline fails?",
                [
                    "No \u2014 skip frame on failure",
                    "Yes \u2014 add fallback (recommended)",
                ],
                current=1
                if (existing and _cfg(existing, "vision", "provider", "type"))
                else 0,
            )

            if use_fb == 1:
                providers = [
                    ("ollama", "Ollama (local)"),
                    ("openai", "OpenAI"),
                    ("anthropic", "Anthropic"),
                    ("google", "Google Gemini"),
                    ("openrouter", "OpenRouter"),
                    ("mistral", "Mistral"),
                    ("together", "Together AI"),
                    ("xai", "xAI"),
                    ("custom", "Custom / Self-hosted"),
                ]
                fb_labels = [p[1] for p in providers]
                current_fb = (
                    next(
                        (
                            i
                            for i, p in enumerate(providers)
                            if p[0] == _cfg(existing, "vision", "provider", "type")
                        ),
                        None,
                    )
                    if existing
                    else 0
                )
                fb_idx = _choice(
                    "Choose fallback provider:", fb_labels, current=current_fb
                )
                fbtype = providers[fb_idx][0]

                fb_model = (
                    _cfg(existing, "vision", "provider", "model", default="") or ""
                )
                fb_url = _cfg(existing, "vision", "provider", "url", default="") or ""
                fb_key = (
                    _cfg(existing, "vision", "provider", "api_key", default="") or ""
                )

                fb_model_in = _text(f"Model name [{fb_model}]: ", default=fb_model)
                fb_url_in = _text(
                    f"Override URL (leave empty for default) [{fb_url}]: ",
                    default=fb_url,
                )
                fb_api_key = ""
                if fbtype != "ollama":
                    masked_kb = "***...***" if fb_key else ""
                    print(f"  API Key")
                    if masked_kb:
                        print(f"    \033[90m[Enter to keep: {masked_kb}]\033[0m")
                    fb_api_key = getpass.getpass("    (leave empty to keep): ").strip()
                    if not fb_api_key and fb_key:
                        fb_api_key = fb_key

                config["vision"]["provider"] = {
                    "type": fbtype,
                    "api_key": fb_api_key,
                    "model": fb_model_in,
                    "url": fb_url_in,
                }
                print(
                    f"\n  \033[32m[OK]\033[0m Fallback provider configured ({fbtype})."
                )

        _section("Summary")

        mode_labels_display = {
            "local": "Local",
            "tunnel": "SSH Tunnel",
            "remote": "Remote",
        }
        display_mode = mode_labels_display.get(
            config["gateway"]["mode"], config["gateway"]["mode"]
        )
        display_vision = (
            "OpenClaw image"
            if vision_idx == 0
            else (
                f"OCR ({config.get('ocr', {}).get('library', '?')})"
                if vision_idx == 1
                else f"Vision API ({config.get('vision', {}).get('provider', {}).get('type', '?')})"
            )
        )

        gw_url = config["gateway"].get("url", "")
        gw_mode = display_mode
        analysis = display_vision
        has_fb = _cfg(config, "vision", "provider", "type")
        fb_val = (
            f"\033[36mYes \u2014 {has_fb}\033[0m" if has_fb else "\033[90mNone\033[0m"
        )
        print(f"  \033[90m  Gateway URL:\033[0m   \033[1m{gw_url}\033[0m")
        print(f"  \033[90m  Gateway mode:\033[0m \033[36m{gw_mode}\033[0m")
        print(f"  \033[90m  Analysis:\033[0m     \033[36m{analysis}\033[0m")
        print(f"  \033[90m  Fallback:\033[0m     {fb_val}")
        print(
            "  \033[36m\u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\033[0m"
        )
        print()
        print("  \033[90m  Save this configuration?\033[0m")
        confirm = _choice(
            "",
            ["Yes — save and exit", "No — cancel"],
            current=0,
        )
        if confirm != 0:
            print("\n  Setup cancelled.")
            sys.exit(0)

        os.makedirs(config_dir, exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        try:
            os.chmod(config_path, 0o600)
        except OSError:
            pass

        print(f"\n  \033[32m[OK]\033[0m Configuration saved to {config_path}")
        print("  \033[32m[OK]\033[0m Run: python daemon/weruh.py start\n")

    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)

    sys.exit(0)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        run_setup()

    print("[OpenWeruh] Starting daemon...")
    config = load_config()

    capture_config = config.get("capture", {})
    interval = capture_config.get("interval_seconds", 15)
    threshold = capture_config.get("change_threshold", 10)

    capturer = ScreenCapturer(threshold=threshold)
    vision_adapter = VisionProviderAdapter(config)
    ocr_processor = OCRProcessor(config)

    force_text = config.get("vision", {}).get("force_text_mode", False)
    use_ocr = ocr_processor.is_available()
    use_vision_fallback = vision_adapter.enabled

    mode_desc = (
        "OCR Text-Only Mode"
        if use_ocr
        else (
            "Vision API Text-Only Mode"
            if (force_text and use_vision_fallback)
            else "Direct Image Mode"
        )
    )
    print(
        f"[OpenWeruh] Mode: {mode_desc} | Capture every {interval}s | Threshold: {threshold}"
    )

    if use_ocr and not ocr_processor.is_available():
        print("\n[X] OCR is enabled but Tesseract is not installed or not in PATH.")
        print("    Install Tesseract OCR:")
        print("      Windows: choco install tesseract -y")
        print(
            "              OR download from https://github.com/UB-Mannheim/tesseract/wiki"
        )
        print("      macOS:   brew install tesseract")
        print("      Linux:   sudo apt install tesseract-ocr")
        print("\n    After installing, restart the daemon.")
        sys.exit(1)

    try:
        while True:
            changed, frame_path = capturer.capture()
            if changed and frame_path:
                if use_ocr:
                    print("[OpenWeruh] Screen changed \u2014 scanning text via OCR...")
                    text = ocr_processor.scan(frame_path)
                    if text:
                        snippet = text[:120] + ("..." if len(text) > 120 else "")
                        print(f"[OpenWeruh] Extracted: {snippet}")
                        trigger_agent_with_text(text, config)
                    else:
                        print("[OpenWeruh] OCR extracted no text from this frame.")

                elif force_text and use_vision_fallback:
                    print(
                        "[OpenWeruh] Screen changed \u2014 analyzing via Vision API..."
                    )
                    description = vision_adapter.analyze(frame_path)
                    if description:
                        snippet = description[:120] + (
                            "..." if len(description) > 120 else ""
                        )
                        print(f"[OpenWeruh] Vision: {snippet}")
                        trigger_agent_with_text(description, config)
                    else:
                        print(
                            "[OpenWeruh] Vision provider failed to generate description."
                        )

                else:
                    print(
                        "[OpenWeruh] Screen changed \u2014 sending image to OpenClaw..."
                    )
                    success = trigger_agent_with_image(frame_path, config)

                    if not success and use_vision_fallback:
                        print(
                            "[OpenWeruh] OpenClaw failed \u2014 falling back to Vision Provider..."
                        )
                        description = vision_adapter.analyze(frame_path)
                        if description:
                            snippet = description[:120] + (
                                "..." if len(description) > 120 else ""
                            )
                            print(f"[OpenWeruh] Fallback: {snippet}")
                            trigger_agent_with_text(description, config)
                        else:
                            print("[OpenWeruh] Vision Provider failed. Skipping frame.")
                    elif not success:
                        print(
                            "[OpenWeruh] Webhook failed. No fallback configured. Skipping frame."
                        )

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[OpenWeruh] Exiting...")
    finally:
        capturer.close()


if __name__ == "__main__":
    main()
