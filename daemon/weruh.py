import os
import sys
import time
import yaml
import getpass
from capture import ScreenCapturer
from trigger import trigger_agent_with_image, trigger_agent_with_text
from vision import VisionProviderAdapter


def setup_windows_ansi():
    """Enable ANSI escape codes on Windows CMD / PowerShell."""
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            # Enable ENABLE_VIRTUAL_TERMINAL_PROCESSING (0x0004)
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass


# ANSI color codes
RED_ORANGE = "\033[38;2;255;90;20m"  # #FF5A14 — vivid red-orange
INDIGO = "\033[38;2;63;0;255m"  # #3F00FF — indigo / nila biru
RESET = "\033[0m"


# ASCII art split into individual word rows.
# Each line is split at the natural gap between "OPEN" and "WERUH".
# The banner is 87 chars wide; "OPEN" occupies cols 0-43, "WERUH" cols 44+.
SPLIT = 44  # character index where WERUH starts

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


def colorize_line(line: str) -> str:
    """
    Color the OPEN portion (left) red-orange and
    the WERUH portion (right) indigo-blue.
    """
    left = line[:SPLIT]
    right = line[SPLIT:]
    return f"{RED_ORANGE}{left}{RESET}{INDIGO}{right}{RESET}"


def print_banner():
    setup_windows_ansi()
    print()
    for line in BANNER_LINES:
        print(colorize_line(line))
    print("\n" + " " * 35 + f"{RED_ORANGE}S E T U P{RESET}\n")


def load_config():
    # Use environment variable or default
    config_path = os.environ.get(
        "OPENWERUH_CONFIG", os.path.expanduser("~/.config/openweruh/weruh.yaml")
    )
    if not os.path.exists(config_path):
        print(
            f"Config not found at {config_path}. Falling back to example config if exists..."
        )
        config_path = os.path.join(
            os.path.dirname(__file__), "..", "config", "weruh.example.yaml"
        )
        if not os.path.exists(config_path):
            print("No config file found. Please run setup or copy weruh.example.yaml.")
            sys.exit(1)

    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_choice(prompt, choices):
    print(prompt)
    for i, choice in enumerate(choices, 1):
        print(f"  {i}) {choice}")
    while True:
        try:
            val = int(input(f"\nSelect an option (1-{len(choices)}): "))
            if 1 <= val <= len(choices):
                return val - 1
            print("Invalid choice. Try again.")
        except ValueError:
            print("Please enter a number.")
        except KeyboardInterrupt:
            print("\nSetup cancelled.")
            sys.exit(1)


def run_setup():
    print_banner()

    try:
        # 1. Gateway Location
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

        token = getpass.getpass("? Hook token (from openclaw.json → hooks.token): ")

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

        # 2. Vision Provider
        print()
        vision_idx = get_choice(
            "? Has your OpenClaw already been configured with a vision-capable imageModel?",
            [
                "Yes — I have already set an imageModel (primary path is sufficient)",
                "Not sure — add a fallback vision provider",
            ],
        )

        if vision_idx == 1:
            print()
            providers = [
                ("ollama", "Ollama (local, full privacy)"),
                ("openai", "OpenAI (GPT-4o / GPT-4.1)"),
                ("anthropic", "Anthropic (Claude Sonnet / Haiku)"),
                ("google", "Google (Gemini Flash / Pro)"),
                ("openrouter", "OpenRouter (access 200+ models via one API)"),
                ("mistral", "Mistral (Pixtral)"),
                ("together", "Together AI (Llama Vision)"),
                ("xai", "xAI (Grok Vision)"),
                (
                    "custom",
                    "Custom / Self-hosted (LiteLLM, vLLM, LMStudio, Azure, etc.)",
                ),
            ]
            p_idx = get_choice("? Choose a vision provider:", [p[1] for p in providers])
            provider_type = providers[p_idx][0]

            api_key = ""
            if provider_type not in ["ollama"]:
                api_key = getpass.getpass(f"? {provider_type.capitalize()} API Key: ")

            model = input("? Model name (e.g., gpt-4o, llava:13b): ").strip()
            override_url = input("? Override URL? (leave empty for default): ").strip()

            config["vision"] = {
                "provider": {
                    "type": provider_type,
                    "api_key": api_key,
                    "model": model,
                    "url": override_url,
                }
            }
            print(f"\n✓ {provider_type.capitalize()} provider configured as fallback")
        else:
            print("\n✓ Skipping fallback vision provider configuration")

        # Save to ~/.config/openweruh/weruh.yaml
        config_dir = os.path.expanduser("~/.config/openweruh")
        os.makedirs(config_dir, exist_ok=True)
        config_path = os.path.join(config_dir, "weruh.yaml")

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        # Try to set permissions securely (Unix only)
        try:
            os.chmod(config_path, 0o600)
        except OSError:
            pass

        print(f"\n✓ Configuration saved securely to {config_path}")
        print("✓ OpenWeruh is ready. Run: python daemon/weruh.py start\n")

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

    print(
        f"[OpenWeruh] Running capture loop every {interval}s with threshold {threshold}..."
    )

    try:
        while True:
            changed, frame_path = capturer.capture()
            if changed and frame_path:
                print("[OpenWeruh] Screen changed, triggering webhook...")
                success = trigger_agent_with_image(frame_path, config)

                if not success and vision_adapter.enabled:
                    print(
                        "[OpenWeruh] Primary webhook failed, falling back to Vision Provider..."
                    )
                    description = vision_adapter.analyze(frame_path)
                    if description:
                        print(f"[OpenWeruh] Vision description: {description}")
                        trigger_agent_with_text(description, config)
                    else:
                        print(
                            "[OpenWeruh] Vision Provider failed to generate description."
                        )
                elif not success:
                    print(
                        "[OpenWeruh] Webhook failed, no Vision Provider configured. Skipping frame."
                    )
            time.sleep(interval)

    except KeyboardInterrupt:
        print("[OpenWeruh] Exiting daemon...")
    finally:
        capturer.close()


if __name__ == "__main__":
    main()
