import os
import sys
import time
import yaml
import getpass
import httpx
from capture import ScreenCapturer
from trigger import trigger_agent_with_image, trigger_agent_with_text
from vision import VisionProviderAdapter
from ocr import OCRProcessor


def setup_windows_ansi():
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


def get_choice(prompt, choices):
    print(prompt)
    for i, choice in enumerate(choices, 1):
        print(f"  {i}) {choice}")
    while True:
        try:
            val = int(input(f"\nSelect an option (1-{len(choices)}): "))
            if 1 <= val <= len(choices):
                return val - 1
            print("  Invalid choice. Try again.")
        except ValueError:
            print("  Please enter a number.")
        except KeyboardInterrupt:
            print("\n\nSetup cancelled.")
            sys.exit(1)


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


def run_setup():
    print_banner()
    try:
        while True:
            gw_idx = get_choice(
                "? Where is your OpenClaw Gateway running?",
                [
                    "On this same machine (local)",
                    "On a remote server (SSH tunnel)",
                    "On a remote server (public URL / Tailscale)",
                ],
            )
            mode = ["local", "tunnel", "remote"][gw_idx]
            default_url = "http://127.0.0.1:18789" if mode != "remote" else "https://"
            url = input(f"? Gateway URL [{default_url}]: ").strip() or default_url
            token = getpass.getpass(
                "? Hook token (from openclaw.json \u2192 hooks.token): "
            ).strip()
            if not token:
                print("  [X] Hook token cannot be empty!\n")
                continue

            if test_gateway_connection(url, token):
                break
            print("\nLet's try configuring the Gateway again.\n")

        config = {
            "gateway": {"mode": mode, "url": url, "hook_token": token},
            "persona": {
                "mode": "skeptic",
                "language": "en",
                "tone": "casual",
                "intervention_threshold": "medium",
            },
            "capture": {
                "interval_seconds": 15,
                "change_threshold": 10,
                "active_hours": "07:00-23:00",
                "notify_after_idle_minutes": 5,
            },
        }

        print()
        vision_idx = get_choice(
            "? How should screen content be analyzed?",
            [
                "OpenClaw has a vision-capable AI model (send image directly \u2014 recommended)",
                "Text-Only Mode: extract visible TEXT via OCR library (no LLM needed)",
                "Text-Only Mode: use Vision API/LLM to DESCRIBE the screen (fallback if OpenClaw fails)",
            ],
        )

        if vision_idx == 0:
            print("  [OK] OpenClaw will receive raw images.")
            print(
                "       Make sure your OpenClaw is configured with a vision-capable imageModel."
            )
            print(
                "       Daemon will auto-fallback to vision.provider if OpenClaw returns an error."
            )

        elif vision_idx == 1:
            print()
            ocr_lib_idx = get_choice(
                "? Choose an OCR library:",
                [
                    "Tesseract OCR (pytesseract) \u2014 fastest",
                    "EasyOCR \u2014 better for complex layouts, slower",
                ],
            )
            ocr_lib = "pytesseract" if ocr_lib_idx == 0 else "easyocr"

            if ocr_lib == "pytesseract":
                try:
                    import shutil

                    if not shutil.which("tesseract") and not os.path.exists(
                        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
                    ):
                        print()
                        print("  [X] Tesseract OCR is not installed!")
                        print()
                        print("  Install Tesseract OCR first:")
                        print("    Windows: choco install tesseract -y")
                        print(
                            "            OR download from https://github.com/UB-Mannheim/tesseract/wiki"
                        )
                        print("    macOS:   brew install tesseract")
                        print("    Linux:   sudo apt install tesseract-ocr")
                        print()
                        print("  After installing, run setup again.")
                        sys.exit(1)
                except Exception:
                    pass

            lang = (
                input(
                    "? OCR language codes (e.g. eng, eng+ind, eng+ara) [eng+ind]: "
                ).strip()
                or "eng+ind"
            )

            config["ocr"] = {
                "enabled": True,
                "library": ocr_lib,
                "lang": lang,
            }
            config["vision"] = {"provider": {}}
            print(
                f"\n  [OK] Text-Only Mode enabled using {ocr_lib}. OpenClaw will receive plain text."
            )

        elif vision_idx == 2:
            print()
            providers = [
                ("ollama", "Ollama (local, full privacy)"),
                ("openai", "OpenAI (GPT-4o / GPT-4.1)"),
                ("anthropic", "Anthropic (Claude Sonnet / Haiku)"),
                ("google", "Google (Gemini Flash / Pro)"),
                ("openrouter", "OpenRouter (access 200+ models)"),
                ("mistral", "Mistral (Pixtral)"),
                ("together", "Together AI (Llama Vision)"),
                ("xai", "xAI (Grok Vision)"),
                ("custom", "Custom / Self-hosted (LiteLLM, vLLM, Azure, etc.)"),
            ]
            p_idx = get_choice("? Choose a vision provider:", [p[1] for p in providers])
            provider_type = providers[p_idx][0]

            api_key = ""
            if provider_type != "ollama":
                api_key = getpass.getpass(f"? {provider_type.capitalize()} API Key: ")

            model = input("? Model name (e.g. gemini-2.5-flash, llava:13b): ").strip()
            override_url = input("? Override URL? (leave empty for default): ").strip()

            config["vision"] = {
                "provider": {
                    "type": provider_type,
                    "api_key": api_key,
                    "model": model,
                    "url": override_url,
                },
            }
            print(f"\n  [OK] Vision provider ({provider_type}) configured.")

        if vision_idx in [0, 2]:
            print()
            use_fb = (
                get_choice(
                    "? Configure a fallback Vision Provider for when OpenClaw image pipeline fails?",
                    [
                        "No \u2014 only use OpenClaw directly (skip frame on failure)",
                        "Yes \u2014 add Ollama / API as fallback (recommended)",
                    ],
                )
                == 1
            )

            if use_fb:
                print()
                providers = [
                    ("ollama", "Ollama (local, full privacy)"),
                    ("openai", "OpenAI"),
                    ("anthropic", "Anthropic"),
                    ("google", "Google Gemini"),
                    ("openrouter", "OpenRouter"),
                    ("mistral", "Mistral"),
                    ("together", "Together AI"),
                    ("xai", "xAI"),
                    ("custom", "Custom / Self-hosted"),
                ]
                p_idx = get_choice(
                    "? Choose fallback provider:", [p[1] for p in providers]
                )
                provider_type = providers[p_idx][0]

                api_key = ""
                if provider_type != "ollama":
                    api_key = getpass.getpass(
                        f"? {provider_type.capitalize()} API Key: "
                    )

                model = input("? Model name: ").strip()
                override_url = input(
                    "? Override URL? (leave empty for default): "
                ).strip()

                config.setdefault("vision", {"provider": {}})
                config["vision"]["provider"] = {
                    "type": provider_type,
                    "api_key": api_key,
                    "model": model,
                    "url": override_url,
                }
                print(f"\n  [OK] Fallback provider ({provider_type}) configured.")

        config_dir = os.path.expanduser("~/.config/openweruh")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "weruh.yaml")

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        try:
            os.chmod(config_path, 0o600)
        except OSError:
            pass

        print(f"\n  [OK] Configuration saved to {config_path}")
        print("  [OK] OpenWeruh is ready. Run: python daemon/weruh.py start\n")

    except KeyboardInterrupt:
        print("\nSetup cancelled.")
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
