import httpx
from typing import Dict, Optional


def trigger_agent_with_image(frame_path: str, config: Dict) -> bool:
    """Primary path: send image to OpenClaw webhook."""
    gateway_config = config.get("gateway", {})
    url = f"{gateway_config.get('url', 'http://127.0.0.1:18789')}/hooks/agent"
    token = gateway_config.get("hook_token", "")

    headers = {"Authorization": f"Bearer {token}"}

    try:
        with open(frame_path, "rb") as f:
            files = {"media": ("weruh-frame.jpg", f, "image/jpeg")}
            data = {
                "message": "[WERUH] Screen attachment ready. Apply active persona.",
                "name": "OpenWeruh",
                "sessionKey": "hook:weruh:screen",
                "wakeMode": "now",
                "deliver": True,
                "channel": "last",
            }

            with httpx.Client(timeout=10) as client:
                response = client.post(url, data=data, files=files, headers=headers)
                response.raise_for_status()
                return True
    except Exception as e:
        print(f"[Trigger] Primary path failed: {e}")
        return False


def trigger_agent_with_text(text_description: str, config: Dict) -> bool:
    """Fallback path: send text description to OpenClaw webhook."""
    gateway_config = config.get("gateway", {})
    url = f"{gateway_config.get('url', 'http://127.0.0.1:18789')}/hooks/agent"
    token = gateway_config.get("hook_token", "")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    data = {
        "message": f"[WERUH] Screen context text fallback: {text_description}. Apply active persona.",
        "name": "OpenWeruh",
        "sessionKey": "hook:weruh:screen",
        "wakeMode": "now",
        "deliver": True,
        "channel": "last",
    }

    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(url, json=data, headers=headers)
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"[Trigger] Fallback text path failed: {e}")
        return False
