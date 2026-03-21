import base64
import httpx
import json

VISION_PROMPT = "Provide a concise 1-sentence description of what the user is currently doing or looking at on this screen."


class VisionProviderAdapter:
    def __init__(self, config):
        self.config = config.get("vision", {}).get("provider", {})
        self.provider_type = self.config.get("type")
        self.api_key = self.config.get("api_key", "")
        self.model = self.config.get("model", "")
        self.url = self.config.get("url", "")
        self.timeout = self.config.get("timeout_seconds", 30)

        if not self.provider_type:
            self.enabled = False
        else:
            self.enabled = True

        self._set_defaults()

    def _set_defaults(self):
        if not self.url:
            if self.provider_type == "openai":
                self.url = "https://api.openai.com/v1/chat/completions"
            elif self.provider_type == "anthropic":
                self.url = "https://api.anthropic.com/v1/messages"
            elif self.provider_type == "google":
                self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            elif self.provider_type == "openrouter":
                self.url = "https://openrouter.ai/api/v1/chat/completions"
            elif self.provider_type == "ollama":
                self.url = "http://localhost:11434/api/chat"
            elif self.provider_type == "mistral":
                self.url = "https://api.mistral.ai/v1/chat/completions"
            elif self.provider_type == "together":
                self.url = "https://api.together.xyz/v1/chat/completions"
            elif self.provider_type == "xai":
                self.url = "https://api.x.ai/v1/chat/completions"

    def analyze(self, image_path: str):
        if not self.enabled:
            return None

        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")

        try:
            if self.provider_type == "anthropic":
                return self._analyze_anthropic(b64_img)
            elif self.provider_type == "google":
                return self._analyze_google(b64_img)
            else:
                return self._analyze_openai_compatible(b64_img)
        except Exception as e:
            print(f"[Vision Fallback Error] {e}")
            return None

    def _analyze_openai_compatible(self, b64_img: str):
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"},
                        },
                        {"type": "text", "text": VISION_PROMPT},
                    ],
                }
            ],
            "max_tokens": 150,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self.url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _analyze_anthropic(self, b64_img: str):
        payload = {
            "model": self.model,
            "max_tokens": 150,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": b64_img,
                            },
                        },
                        {"type": "text", "text": VISION_PROMPT},
                    ],
                }
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self.url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["content"][0]["text"]

    def _analyze_google(self, b64_img: str):
        payload = {
            "contents": [
                {
                    "parts": [
                        {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}},
                        {"text": VISION_PROMPT},
                    ]
                }
            ]
        }
        headers = {"Content-Type": "application/json", "x-goog-api-key": self.api_key}

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(self.url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
