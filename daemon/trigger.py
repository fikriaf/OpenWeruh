import httpx
import base64
from typing import Dict


def trigger_agent_with_image(frame_path: str, config: Dict) -> bool:
    """Primary path: send image to OpenClaw webhook via base64 JSON payload."""
    gateway_config = config.get("gateway", {})
    url = (
        f"{gateway_config.get('url', 'http://127.0.0.1:18789').rstrip('/')}/hooks/agent"
    )
    token = gateway_config.get("hook_token", "")

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with open(frame_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        data = {
            "message": "[WERUH] Screen attachment ready. Apply active persona.",
            "name": "OpenWeruh",
            "sessionKey": "hook:weruh:screen",
            "wakeMode": "now",
            "deliver": True,
            "channel": "last",
            "media": [f"data:image/jpeg;base64,{img_b64}"],
        }

        with httpx.Client(timeout=20) as client:
            response = client.post(url, json=data, headers=headers)

            if response.status_code >= 400:
                print(
                    f"[Trigger] Image path failed: HTTP {response.status_code} {response.reason_phrase}"
                )
                print(f"[Trigger] Response: {response.text}")
                if "allowRequestSessionKey" in response.text:
                    print(
                        "\n  [X] Enable 'hooks.allowRequestSessionKey=true' in OpenClaw config.\n"
                    )
                return False

            return True
    except httpx.RequestError as e:
        print(f"[Trigger] Image path connection error: {e}")
        return False
    except Exception as e:
        print(f"[Trigger] Image path error: {e}")
        return False


def trigger_agent_with_text(text_description: str, config: Dict) -> bool:
    """Send text-only context to OpenClaw webhook (for OCR or Vision Provider mode)."""
    gateway_config = config.get("gateway", {})
    url = (
        f"{gateway_config.get('url', 'http://127.0.0.1:18789').rstrip('/')}/hooks/agent"
    )
    token = gateway_config.get("hook_token", "")

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = {
        "message": f"[WERUH] Screen context: {text_description}",
        "name": "OpenWeruh",
        "sessionKey": "hook:weruh:text",
        "wakeMode": "now",
        "deliver": False,
        "channel": "last",
    }

    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(url, json=data, headers=headers)

            if response.status_code >= 400:
                print(f"[Trigger] Text path failed: HTTP {response.status_code}")
                print(f"[Trigger] Response: {response.text}")
                return False

            return True
    except httpx.RequestError as e:
        print(f"[Trigger] Text path connection error: {e}")
        return False
    except Exception as e:
        print(f"[Trigger] Text path error: {e}")
        return False
