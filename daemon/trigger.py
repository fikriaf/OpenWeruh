import httpx
from typing import Dict, Optional


def trigger_agent_with_image(frame_path: str, config: Dict) -> bool:
    """Primary path: send image to OpenClaw webhook."""
    gateway_config = config.get("gateway", {})
    url = (
        f"{gateway_config.get('url', 'http://127.0.0.1:18789').rstrip('/')}/hooks/agent"
    )
    token = gateway_config.get("hook_token", "")

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with open(frame_path, "rb") as f:
            files = {"media": ("weruh-frame.jpg", f, "image/jpeg")}
            data = {
                "message": "[WERUH] Screen attachment ready. Apply active persona.",
                "name": "OpenWeruh",
                "sessionKey": "hook:weruh:screen",
                "wakeMode": "now",
                "deliver": "true",
                "channel": "last",
            }

            with httpx.Client(timeout=10) as client:
                response = client.post(url, data=data, files=files, headers=headers)

                if response.status_code >= 400:
                    print(
                        f"[Trigger] Primary path failed: {response.status_code} {response.reason_phrase}"
                    )
                    print(f"[Trigger] Server response: {response.text}")
                    return False

                return True
    except httpx.RequestError as e:
        print(f"[Trigger] Primary path connection error: {e}")
        return False
    except Exception as e:
        print(f"[Trigger] Primary path error: {e}")
        return False


def trigger_agent_with_text(text_description: str, config: Dict) -> bool:
    """Fallback path: send text description to OpenClaw webhook."""
    gateway_config = config.get("gateway", {})
    url = (
        f"{gateway_config.get('url', 'http://127.0.0.1:18789').rstrip('/')}/hooks/agent"
    )
    token = gateway_config.get("hook_token", "")

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

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

            if response.status_code >= 400:
                print(
                    f"[Trigger] Fallback text path failed: {response.status_code} {response.reason_phrase}"
                )
                print(f"[Trigger] Server response: {response.text}")
                return False

            return True
    except httpx.RequestError as e:
        print(f"[Trigger] Fallback text path connection error: {e}")
        return False
    except Exception as e:
        print(f"[Trigger] Fallback text path error: {e}")
        return False
