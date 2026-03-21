import os
import sys
import time
import yaml
from capture import ScreenCapturer
from trigger import trigger_agent_with_image, trigger_agent_with_text
from vision import VisionProviderAdapter


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


def run_setup():
    print("OpenWeruh Setup")
    print("───────────────")
    # A real setup would be interactive using rich/prompt_toolkit.
    # We will provide a stub here.
    print("Interactive setup is not fully implemented in this script version.")
    print("Please edit ~/.config/openweruh/weruh.yaml manually.")
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
