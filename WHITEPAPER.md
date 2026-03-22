# OpenWeruh
## Whitepaper v0.1 — Proactive Screen-Aware Context Layer for OpenClaw

> *Weruh* (Javanese) — to see, to know, to understand without being asked.

---

## Table of Contents

1. Background & Motivation
2. Problem Statement
3. Vision & Project Positioning
4. System Architecture
5. Technical Components
6. OpenClaw Foundations Used
7. Workflow
8. Persona & Configuration Modes
9. Deployment Modes
10. Troubleshooting
11. Security & Privacy
12. Repository Structure
13. Contributing & License
14. References

---

## 1. Background & Motivation

OpenClaw is a locally-running AI agent gateway that has grown into an open ecosystem with more than 13,700+ skills available on ClawHub (as of February 2026). The strength of OpenClaw lies in its modular architecture: skills, cron, hooks, and webhooks work together to form an agent that can be proactive.

However, there is one dimension that the ecosystem has not yet touched: **what is currently happening on the user's screen**.

All proactivity in OpenClaw is still time-based (cron, heartbeat) or driven by external events (webhooks from email, GitHub, etc.). There is no bridge between **real-time visual context on the screen** and the intelligence the agent already possesses.

OpenWeruh exists to fill that gap.

---

## 2. Problem Statement

### Problem 1: The Agent Is Still Blind

OpenClaw agents can read calendars, emails, and files — but cannot see what the user is currently working on. If the user is reading an article containing a false claim, the agent does not know. If the user is staring at code with a bug, the agent does not know.

### Problem 2: Proactivity Is Still Time-Based, Not Context-Based

The OpenClaw heartbeat runs on a fixed interval (default 30 minutes). This is powerful, but blind to important moments happening between intervals. A wrong decision made by the user within 5 minutes will not be caught by the heartbeat.

### Problem 3: Existing Screen Capture Is Reactive

The `screen-monitor` skill on ClawHub only works when the user explicitly calls it: *"take a screenshot and tell me what you see."* This is not proactivity — it is still reactive behavior in a new wrapper.

### Problem 4: Screen Permission on macOS Cannot Be Accessed by a Daemon

The OpenClaw Gateway runs as a background process (daemon). On macOS, screen recording permission can only be granted to an interactive GUI process, not a headless daemon. No skill currently solves this fundamental problem in a cross-platform way.

---

## 3. Vision & Project Positioning

**OpenWeruh is not a replacement for existing skills. OpenWeruh is a new layer beneath them.**

```
┌─────────────────────────────────────────┐
│          User (Laptop/PC Screen)        │
└──────────────────┬──────────────────────┘
                   │ visual context
┌──────────────────▼──────────────────────┐
│         OpenWeruh Layer                 │
│  (screen daemon + decision engine)      │
└──────────────────┬──────────────────────┘
                   │ webhook / system event
┌──────────────────▼──────────────────────┐
│         OpenClaw Gateway                │
│  (agent + skills + cron + hooks)        │
└──────────────────┬──────────────────────┘
                   │ WhatsApp / Telegram / notification
┌──────────────────▼──────────────────────┐
│          User (Channel)                 │
└─────────────────────────────────────────┘
```

OpenWeruh works as a supporting technology — users can still install other skills, configure other crons, and OpenWeruh will not conflict with those components because it uses OpenClaw's official interfaces (webhook + system event).

---

## 4. System Architecture

OpenWeruh consists of four main components:

```
openweruh/
├── daemon/              ← Python daemon (native screen capture)
├── skill/               ← SKILL.md for agent instructions
├── hook/                ← TypeScript hook (gateway:startup lifecycle)
└── config/              ← weruh.yaml (persona, threshold, mode)
```

### 4.1 Separation of Concerns

| Component | Language | Responsibility |
|---|---|---|
| `daemon/` | Python | Capture screen, detect changes, send to gateway |
| `skill/` | Markdown | Teach the agent how to respond to screen context |
| `hook/` | TypeScript | Inject `screen.context` tool at gateway startup |
| `config/` | YAML | Persona, sensitivity threshold, active hours |

---

## 5. Technical Components

### 5.1 Screen Daemon (`daemon/weruh.py`)

The daemon is a native process that runs separately from the OpenClaw Gateway. This solves the macOS permission problem because this daemon is **not** part of the gateway process.

**Libraries used (already available):**

`mss` — ultra-fast cross-platform screenshot module, pure Python, using ctypes directly to the OS API:
- Windows: `BitBlt` (GDI)
- macOS: `CGGetActiveDisplayList`
- Linux: `XGetImage` (X11) or `grim` (Wayland)

```python
# Basic capture with mss
from mss import mss

with mss() as sct:
    screenshot = sct.grab(sct.monitors[1])  # first monitor
    # → ImageData object, ready to be encoded to base64
```

The daemon operates in a loop:

```
capture → hash frame → compare with previous frame →
if significant change → save to /tmp/weruh-frame.jpg →
  [ocr.enabled = true]
             → extract visible TEXT via OCR (pytesseract / easyocr)
             → send ONLY text to OpenClaw webhook
             (no LLM, no API cost, fully offline)
  [ocr.enabled = false]
             send image to OpenClaw webhook
             │
        OpenClaw success? ── yes ── done
                │
               no
                │
         vision.provider configured?
               yes ──→ describe via LLM
                        send text to OpenClaw
               no ──→ skip frame
```

**Change detection** uses perceptual hashing (pHash) via the `imagehash` library. Only frames that differ meaningfully are sent to the agent — not every screenshot. This keeps API costs low.

**Threshold** is configured in `weruh.yaml`:

```yaml
capture:
  interval_seconds: 60        # how often screenshots are taken
  change_threshold: 10        # minimum pHash distance to trigger
  active_hours: "07:00-23:00" # only active during working hours
```

### 5.2 SKILL.md (`skill/SKILL.md`)

The skill teaches the OpenClaw agent how to process incoming screen context. The format follows the official OpenClaw specification with YAML frontmatter:

```yaml
---
name: openweruh
description: >
  Proactive screen context processor. Triggered when screen.context payload
  arrives via webhook. Analyze the visual content, apply the configured persona
  mode, and decide whether the observation warrants a proactive notification
  to the user. Use this skill whenever a [WERUH] system event is received.
version: 1.0.0
metadata:
  openclaw:
    emoji: "👁️"
    requires:
      bins: []
    alwaysActive: false
---
```

The instructions inside SKILL.md explain to the agent:
- When to intervene and when to stay silent
- How to apply the configured persona
- The notification format sent to the user
- How to avoid false positives and notification spam

### 5.3 TypeScript Hook (`hook/weruh-boot.ts`)

The hook uses the OpenClaw Hook API with the `gateway:startup` event to ensure OpenWeruh is registered every time the gateway starts:

```typescript
import type { HookHandler } from "openclaw/hooks";

const handler: HookHandler = async (event) => {
  if (event.type !== "gateway" || event.action !== "startup") return;

  // Register that the agent now has the screen.context tool
  event.messages.push(
    "[OpenWeruh] Screen context layer active. " +
    "Tool screen.context is available for visual analysis."
  );
};

export default handler;
```

This hook is lightweight and non-blocking — following the official OpenClaw pattern that recommends `void processInBackground(event)` for async work so it does not block command processing.

### 5.4 Webhook Trigger

The daemon sends the screenshot directly to OpenClaw as a file attachment. OpenClaw is responsible for forwarding it to the `imageModel` already configured by the user in the gateway — OpenWeruh does not choose or call the vision model itself.

```python
import httpx

def trigger_agent_with_image(frame_path: str, config: dict):
    """Primary path: send image to OpenClaw, let OpenClaw's imageModel handle it."""
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
        headers = {"Authorization": f"Bearer {config['gateway']['hook_token']}"}

        response = httpx.post(
            f"{config['gateway']['url']}/hooks/agent",
            data=data,
            files=files,
            headers=headers,
            timeout=10
        )
        return response.status_code == 200
```

If the primary path fails (image dropped by OpenClaw due to a pipeline bug or the model does not support vision), the daemon falls back to the Vision Provider configured by the user.

### 5.5 Vision Engine — OCR, OpenClaw, & Fallback

#### Text-Only Mode: OCR Library (Recommended for Text-Only LLMs)

When `ocr.enabled: true` in `weruh.yaml`, OpenWeruh uses a local OCR library to extract visible text from screenshots — completely bypassing any LLM.

This solves the `tools.profile allowlist contains unknown entries (image)` error that text-only LLMs throw. No API key, no latency, no cost.

**Two OCR engines supported:**

**pytesseract** (recommended — fast):
```bash
pip install pytesseract pillow
# Windows: choco install tesseract -y
# macOS:  brew install tesseract
# Linux:  sudo apt install tesseract-ocr
```
```yaml
ocr:
  enabled: true
  library: "pytesseract"
  lang: "eng+ind"
```

**EasyOCR** (better accuracy, slower, GPU preferred):
```bash
pip install easyocr
```
```yaml
ocr:
  enabled: true
  library: "easyocr"
  lang: "eng+ind"
```

#### Primary Path: OpenClaw `imageModel`

OpenClaw already has a complete built-in vision pipeline. When it receives an image via webhook, the gateway automatically checks whether the configured model supports vision, then attaches the image to the API request. The user configures this in OpenClaw as usual:

```bash
# In OpenClaw — set the vision model (done by the user, not OpenWeruh)
openclaw models set-image google/gemini-flash-1.5-8b
# or
openclaw models set-image llava:13b   # if using local Ollama
```

OpenWeruh does not need to know which model is being used — just send the image to the webhook and let the gateway handle it.

#### Fallback Path: Custom Vision Provider (Optional)

Because OpenClaw currently has a bug where images from certain channels are dropped before reaching the agent, and Ollama models are not always detected as vision-capable, OpenWeruh provides a fallback path with an independently configured vision provider.

The fallback is only active if:
1. The primary path fails (error response or image not processed)
2. The user fills in `vision.provider` in `weruh.yaml`

#### Provider Configuration in `weruh.yaml`

```yaml
# Text-Only Mode (OCR) — extract visible text, no LLM needed
ocr:
  enabled: false
  library: "pytesseract"   # pytesseract | easyocr
  lang: "eng+ind"          # language codes

# Vision Provider (Fallback) — only used when OpenClaw's image pipeline fails
vision:
  provider:
    type: "ollama"             # openai | anthropic | google | ollama | openrouter | mistral | together | xai | custom
    url: ""                   # leave empty = use default URL
    api_key: ""               # empty for local Ollama
    model: "llava:13b"        # model name
    timeout_seconds: 30
```

**Reference for known providers:**

| `type` | Default URL | Example Model | API Key |
|---|---|---|---|
| `openai` | `https://api.openai.com/v1/chat/completions` | `gpt-4.1`, `gpt-4o` | Required |
| `anthropic` | `https://api.anthropic.com/v1/messages` | `claude-sonnet-4-6` | Required |
| `google` | `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` | `gemini-2.0-flash` | Required |
| `openrouter` | `https://openrouter.ai/api/v1/chat/completions` | `google/gemini-flash-1.5-8b` | Required |
| `ollama` | `http://localhost:11434/api/chat` | `llava:13b`, `moondream2` | Not required |
| `mistral` | `https://api.mistral.ai/v1/chat/completions` | `pixtral-large-latest` | Required |
| `together` | `https://api.together.xyz/v1/chat/completions` | `meta-llama/Llama-3.2-11B-Vision` | Required |
| `xai` | `https://api.x.ai/v1/chat/completions` | `grok-2-vision-latest` | Required |
| `custom` | (must fill `url`) | (must fill `model`) | Optional |

The `url` field is **optional for all types** — if left empty, the default URL in the table above is used. If filled in, that URL is used instead — this enables:
- Self-hosted LiteLLM proxy exposing multiple providers at a single endpoint
- Ollama on LAN (`http://192.168.1.10:11434/api/chat`)
- vLLM, LMStudio, Jan, or any OpenAI-compatible inference server
- Azure OpenAI (`https://{resource}.openai.azure.com/openai/deployments/{model}/chat/completions`)

#### Request Format per Provider

Each provider has a slightly different request format. OpenWeruh handles this internally based on `type`:

**OpenAI-compatible** (`openai`, `openrouter`, `ollama`, `mistral`, `together`, `xai`, `custom`):
```python
# Standard format — all these providers use the same structure
payload = {
    "model": model,
    "messages": [{
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
            },
            {"type": "text", "text": VISION_PROMPT}
        ]
    }],
    "max_tokens": 150
}
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"   # empty/dummy for Ollama
}
# Response: resp.json()["choices"][0]["message"]["content"]
```

**Anthropic** (`anthropic`) — different format, not OpenAI-compatible:
```python
# Anthropic uses a different message structure
payload = {
    "model": model,
    "max_tokens": 150,
    "messages": [{
        "role": "user",
        "content": [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64        # base64 string, not a data URL
                }
            },
            {"type": "text", "text": VISION_PROMPT}
        ]
    }]
}
headers = {
    "Content-Type": "application/json",
    "x-api-key": api_key,              # not Authorization Bearer
    "anthropic-version": "2023-06-01"  # required header
}
# Response: resp.json()["content"][0]["text"]
```

**Google Gemini** (`google`) — different format, URL contains the model name:
```python
# Google uses a different endpoint per model and its own content format
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
payload = {
    "contents": [{
        "parts": [
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": b64        # base64 string
                }
            },
            {"text": VISION_PROMPT}
        ]
    }]
}
headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": api_key          # not Authorization Bearer
}
# Response: resp.json()["candidates"][0]["content"]["parts"][0]["text"]
```

OpenWeruh abstracts these differences in `vision.py` — the user only needs to set `type` in `weruh.yaml`, without knowing which format is being used internally.

#### Full Configuration Examples

```yaml
# Use OpenAI GPT-4o as fallback (default URL)
vision:
  provider:
    type: "openai"
    api_key: "sk-..."
    model: "gpt-4o"

# Use Claude Sonnet as fallback (default URL)
vision:
  provider:
    type: "anthropic"
    api_key: "sk-ant-..."
    model: "claude-sonnet-4-6"

# Use Gemini Flash as fallback (default URL)
vision:
  provider:
    type: "google"
    api_key: "AIza..."
    model: "gemini-2.0-flash"

# Use local Ollama — no API key required
vision:
  provider:
    type: "ollama"
    model: "llava:13b"

# Use Ollama on another LAN machine — override URL
vision:
  provider:
    type: "ollama"
    url: "http://192.168.1.50:11434/api/chat"
    model: "moondream2"

# Use self-hosted LiteLLM proxy exposing all providers
vision:
  provider:
    type: "custom"
    url: "http://localhost:4000/v1/chat/completions"
    api_key: "sk-litellm-key"
    model: "gpt-4o"

# Use Azure OpenAI
vision:
  provider:
    type: "custom"
    url: "https://myresource.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-01"
    api_key: "azure-key"
    model: "gpt-4o"

# Use OpenRouter with a cheap open-source model
vision:
  provider:
    type: "openrouter"
    api_key: "sk-or-..."
    model: "meta-llama/llama-3.2-11b-vision-instruct"

# Use Mistral Pixtral
vision:
  provider:
    type: "mistral"
    api_key: "..."
    model: "pixtral-large-latest"

# Use Together AI (Llama Vision)
vision:
  provider:
    type: "together"
    api_key: "..."
    model: "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo"

# Use xAI Grok Vision
vision:
  provider:
    type: "xai"
    api_key: "xai-..."
    model: "grok-2-vision-latest"
```

#### Full Decision Tree

```
daemon has a new frame
        │
        ├── ocr.enabled = true?
        │     yes ──→ extract TEXT via pytesseract / easyocr
        │               send ONLY text to OpenClaw
        │
        ├── ocr.enabled = false
        │     │
        │     send image to OpenClaw webhook
        │              │
        │     OpenClaw success? ──── yes ──→ done
        │              │
        │             no
        │              │
        │      vision.provider configured?
        │            yes ──→ describe via LLM
        │                      send text to OpenClaw
        │            no ──→ skip frame
```

#### Interactive Setup (via `python daemon/weruh.py setup`)

The setup wizard handles everything in one flow:

1. **Auto-install** skill and hook into OpenClaw directories
2. **OpenClaw config notes** — if OpenClaw is remote, user edits `openclaw.json` where OpenClaw runs:

   ```
   Telegram not reaching you?
     Edit openclaw.json:
       channels.telegram.allowFrom = ["*"],
       channels.telegram.dmPolicy = "open"

   'unknown entries (image)' error?
     Edit openclaw.json:
       tools.profile = "minimal"
   ```

3. **Gateway configuration** — URL, mode (local/tunnel/remote), hook token
4. **Screen analysis mode** — OpenClaw image / OCR / Vision API fallback
5. **Summary** — review and confirm before saving

Configuration is saved to `~/.config/openweruh/weruh.yaml` with permission `600`.

#### No additional external dependencies are required beyond `httpx` and `mss` for the core daemon. The vision fallback is only active if configured by the user.

---

## 6. OpenClaw Foundations Used

OpenWeruh **does not modify OpenClaw's core** in any way. All integrations use existing official interfaces:

### 6.1 Webhook (`/hooks/agent`)

OpenClaw provides an HTTP webhook endpoint that can be called by an external process. This is the main bridge between the daemon and the agent. The endpoint supports `sessionKey` for persistent sessions, so each screen observation builds continuous context in the `hook:weruh:text` session.

**Important — `wakeMode` behavior:**
- By default (no `wakeMode` or `wakeMode: idle`), screen capture is **added to session context** — agent reads it when human sends a message. No new agent run is triggered.
- `wakeMode: now` triggers a **new agent run** every time a capture is sent. This can flood the queue if captures are too frequent. OpenWeruh uses `wakeMode: now` with a **60-second interval** to balance realtime responsiveness with queue stability.

Official documentation: `docs.openclaw.ai/automation/webhook`

### 6.2 Hook API (`gateway:startup`)

The OpenClaw Hook API supports the `gateway:startup` event, called once when the gateway starts. OpenWeruh uses this to register itself without requiring any manual configuration changes by the user.

Hooks are automatically discovered from `~/.openclaw/hooks/` (managed hooks, shared across workspaces).

### 6.3 SKILL.md (AgentSkills spec)

OpenClaw uses AgentSkills-compatible skill folders. The OpenWeruh skill follows the standard YAML frontmatter + natural language instructions format. When a skill is active, OpenClaw injects its instructions into the agent's system prompt with a deterministic cost (97 characters per skill + field lengths).

### 6.4 System Event

For an alternative heartbeat mechanism (optional), OpenWeruh can use the `openclaw system event` CLI to inject context into the main session:

```bash
openclaw system event \
  --text "[WERUH] Screen context: user is reading an article about X" \
  --mode now
```

This is useful as a fallback when webhooks are not configured.

### 6.5 Cron (optional — daily summary heartbeat)

OpenWeruh provides an optional cron job that sends a summary of the day's screen activity to the user each evening:

```bash
openclaw cron add \
  --name "weruh-daily-summary" \
  --cron "0 21 * * *" \
  --session isolated \
  --message "Summarize today's screen context observations from weruh session." \
  --announce \
  --channel last
```

---

## 7. Workflow

### 7.1 Happy Path

```
1. User installs OpenWeruh
   → daemon starts automatically
   → hook registered in ~/.openclaw/hooks/
   → skill registered in ~/.openclaw/skills/
   → weruh.yaml configured with token & gateway URL

2. User works as usual

3. Every 15 seconds (default config):
   → daemon takes a screenshot
   → pHash compared with previous frame
   → If delta < threshold: skip, no API call
   → If delta ≥ threshold: save frame, send to OpenClaw

4. OpenClaw agent processes the image via configured imageModel:
   → Analyzes screen content
   → Generates a short summary: "user is reading a news article about X"
   → Agent evaluates whether to trigger an intervention

5. If trigger is warranted:
   → POST to /hooks/agent with context
   → OpenClaw agent wakes up, loads SKILL.md openweruh
   → Agent applies the active persona mode
   → Agent decides: intervene or stay silent

6. If agent decides to intervene:
   → Notification sent to user's channel (WhatsApp/Telegram)
   → Example: "You've been on Reddit for 45 minutes. Want me to block it for a while?"
```

### 7.2 Change Detection Detail

```python
import imagehash
from PIL import Image

def should_trigger(prev_hash, current_frame, threshold=10):
    img = Image.frombytes("RGB", current_frame.size, current_frame.rgb)
    current_hash = imagehash.phash(img)

    if prev_hash is None:
        return True, current_hash

    delta = prev_hash - current_hash  # Hamming distance
    return delta >= threshold, current_hash
```

A threshold of 10 means the screen must change by roughly 10% of meaningful pixels before triggering. This filters out minor scrolling and UI animations that are not substantive.

---

## 8. Persona & Configuration Modes

This is what differentiates OpenWeruh from a plain screen watcher. The agent has a **character and agenda** configured by the user.

```yaml
# weruh.yaml
persona:
  mode: "skeptic"               # skeptic | researcher | focus | guardian | silent
  language: "en"                # notification language: en | id
  tone: "casual"                # casual | formal
  intervention_threshold: "medium"  # low | medium | high

active_hours: "07:00-23:00"
notify_after_idle_minutes: 5    # wait X minutes of no change before sending

modes:
  skeptic:
    description: "Always look for counter-arguments from what is being read"
    trigger_keywords: ["news", "claim", "fact", "study", "research"]

  researcher:
    description: "Automatically find supporting sources for relevant content"
    trigger_keywords: ["paper", "journal", "definition", "concept"]

  focus:
    description: "Intervene if user drifts from the topic declared at session start"
    requires_session_goal: true

  guardian:
    description: "Monitor duration per app/website, send reminders"
    idle_limit_minutes: 30

  silent:
    description: "Record context without intervention. Only generate daily summary."
```

Each mode has different behavior defined in SKILL.md. The agent reads `weruh.yaml` on every turn to apply the active mode.

---

## 9. Deployment Modes

OpenWeruh is designed to work in three different deployment scenarios. The daemon always runs on the **local machine** (because it needs access to the screen), while the OpenClaw Gateway can be anywhere.

```
┌─────────────────────────────────────────────────────┐
│  OpenWeruh Daemon (ALWAYS on the local machine)     │
│  - Screen capture                                   │
│  - Change detection                                 │
│  - Vision fallback (if configured)                  │
└────────────────────┬────────────────────────────────┘
                     │ POST /hooks/agent
                     │ Bearer: HOOK_TOKEN
          ┌──────────▼──────────────────┐
          │   Transport Layer           │
          │   (depends on deploy mode)  │
          └──────────┬──────────────────┘
                     │
     ┌───────────────┼───────────────────┐
     ▼               ▼                   ▼
 Mode A          Mode B              Mode C
 Local           SSH Tunnel          Remote Public
 same machine    VPS/server          VPS + reverse proxy
```

---

### Mode A — Local (Gateway & Daemon on the Same Machine)

The simplest scenario. OpenClaw and the OpenWeruh daemon run on the same laptop/PC.

```yaml
# ~/.config/openweruh/weruh.yaml
gateway:
  mode: "local"
  url: "http://127.0.0.1:18789"
  hook_token: "token-from-openclaw"
```

How to get the `hook_token`:
```bash
# In OpenClaw, enable webhooks first
openclaw config set hooks.enabled true
openclaw config set hooks.token "your-own-secret"
openclaw config set hooks.allowRequestSessionKey true
# Restart your OpenClaw Gateway to apply changes
```

Or via `openclaw.json`:
```json
{
  "hooks": {
    "enabled": true,
    "token": "long-random-secret"
  }
}
```

---

### Mode B — Remote via SSH Tunnel (Recommended for VPS)

The most common scenario: OpenClaw runs on an always-on VPS/server, the OpenWeruh daemon runs on a local laptop. This is the **deployment model recommended by the official OpenClaw docs** for production.

OpenClaw defaults to `bind: loopback` — the gateway is never exposed directly to the internet. Remote access via SSH tunnel is the official pattern.

```
[Local Laptop]                    [VPS/Server]
  weruh daemon  ──SSH tunnel──▶  127.0.0.1:18789 (OpenClaw)
  :18789 local                   (gateway loopback-only)
```

**SSH Tunnel setup:**
```bash
# Open tunnel from laptop to server
ssh -N -L 18789:127.0.0.1:18789 user@your-vps.com

# For a persistent tunnel (use autossh)
autossh -M 0 -N -L 18789:127.0.0.1:18789 user@your-vps.com
```

**weruh.yaml:**
```yaml
gateway:
  mode: "tunnel"
  url: "http://127.0.0.1:18789"   # via SSH tunnel
  hook_token: "secret-from-server"

  # Optional: OpenWeruh can auto-open the tunnel
  tunnel:
    enabled: true
    host: "user@your-vps.com"
    remote_port: 18789
    local_port: 18789
```

**OpenClaw on server — webhook configuration:**
```bash
# Set via env var on server (before starting OpenClaw)
export OPENCLAW_HOOKS_ENABLED=true
export OPENCLAW_HOOKS_TOKEN="same-secret-as-weruh-yaml"
```

Or in `openclaw.json` on the server:
```json
{
  "hooks": {
    "enabled": true,
    "token": "same-secret-as-weruh-yaml",
    "path": "/hooks"
  }
}
```

> Note: When `AUTH_PASSWORD` is configured in OpenClaw and hooks are enabled, the hooks path **automatically bypasses** HTTP basic auth. OpenClaw validates requests using the hook token independently.

---

### Mode C — Remote via Public URL (Reverse Proxy / Tailscale / Tunnel Service)

For scenarios where the gateway needs to be accessed from multiple devices or SSH tunneling is not practical:

**C1 — Tailscale (recommended for private networks):**
```yaml
gateway:
  mode: "remote"
  url: "https://openclaw.tail1234.ts.net"
  hook_token: "your-secret"
```

Setup on server:
```bash
# Enable Tailscale Serve on the server
tailscale serve https:443 / http://127.0.0.1:18789
```

> Note: `gateway.auth.allowTailscale: true` in OpenClaw config enables Tailscale identity headers for Control UI and WebSocket authentication. HTTP API endpoints (including webhooks) still require token auth.

**C2 — Localtonet / Ngrok (for public access):**
```yaml
gateway:
  mode: "remote"
  url: "https://xxxx.localtonet.com"
  hook_token: "your-secret"
```

**C3 — Nginx/Caddy reverse proxy + Let's Encrypt:**
```yaml
gateway:
  mode: "remote"
  url: "https://openclaw.yourdomain.com"
  hook_token: "your-secret"
  tls_fingerprint: ""  # optional: pin TLS cert (gateway.remote.tlsFingerprint)
```

OpenClaw config on server for Docker deployment:
```bash
# Environment variables in Docker
OPENCLAW_GATEWAY_TOKEN=your-stable-token
OPENCLAW_HOOKS_ENABLED=true
OPENCLAW_HOOKS_TOKEN=your-hook-secret
OPENCLAW_GATEWAY_BIND=loopback  # let nginx handle the expose
```

---

### Credential Resolution Order

OpenWeruh follows the official OpenClaw credential resolution order for consistency:

```
OPENWERUH_GATEWAY_TOKEN (env var)
  → weruh.yaml: gateway.hook_token
  → ~/.openclaw/openclaw.json: gateway.remote.token  (fallback)
```

For security, `gateway.remote.token` is only used as a last resort when no explicit token is provided — following official OpenClaw behavior.

---

### Deployment Mode Comparison

| Aspect | Mode A (Local) | Mode B (SSH Tunnel) | Mode C (Remote) |
|---|---|---|---|
| Setup complexity | Minimal | Moderate | Moderate |
| Skill/Hook install | Direct copy | Agent exec via webhook | Agent exec via webhook |
| Security | Local, safe | Encrypted SSH | Depends on proxy |
| Always-on | No (requires laptop on) | Yes (VPS) | Yes (VPS) |
| Vision fallback | Local / cloud | Local / cloud | Cloud recommended |
| Recommended for | Dev / testing | Personal production | Multi-user / team |

---

### Interactive Installer

The OpenWeruh installer detects local vs. remote deployment and handles component installation accordingly:

```bash
$ python daemon/weruh.py setup

OpenWeruh Setup
───────────────
? Where is your OpenClaw Gateway running?
  ❯ On this same machine (local)
    On a remote server (SSH tunnel)
    On a remote server (public URL / Tailscale)

? Gateway URL: https://openclaw.tail1234.ts.net
? Hook token (from openclaw.json → hooks.token): ****

✓ Gateway connection successful

[!] Remote mode detected.
    OpenWeruh components will be installed on the remote server
    after gateway connection is verified.

┌─ Screen Analysis ──────────────────────────────────────────────────┐
? How should screen content be analyzed?
  ❯ OpenClaw imageModel (recommended)
    Text-Only Mode: OCR (no LLM needed)
    Text-Only Mode: Vision API

✓ Remote install triggered (agent will execute commands)
OpenWeruh is ready. Run: python daemon/weruh.py start
```

**Remote install flow (Mode B / C):**  
When a remote gateway is detected, the installer sends install instructions via the OpenClaw webhook to the agent session. The OpenClaw agent — running on the server — receives the message and executes the install commands via its `exec` tool:

```bash
git clone https://github.com/fikriaf/OpenWeruh.git
npx clawhub install openweruh --no-input
openclaw hooks install OpenWeruh/hook/weruh-boot
```

This means OpenWeruh components are installed **by OpenClaw itself** on the server — no SSH, no manual file transfer needed.

---

## 10. Roadmap

### v0.1 — Foundation (Month 1–2)

- Python daemon with `mss` + `imagehash`
- Basic SKILL.md
- `gateway:startup` hook
- Webhook integration with OpenClaw
- Platform support: Linux (X11), Windows
- Modes: `silent` and `guardian`
- Configuration via `weruh.yaml`
- Demo video

### v0.2 — Vision Intelligence (Month 2–3)

- Vision provider fallback with full multi-provider support (Ollama, OpenAI, Anthropic, Google, OpenRouter, Mistral, Together, xAI, custom)
- Modes: `skeptic` and `researcher`
- macOS support (solve permission via minimal GUI bridge app)
- Daily summary via cron
- Publish to ClawHub

### v0.3 — Advanced Context (Month 3+)

- `focus` mode with session goal declaration
- Persistent context memory across sessions
- Browser extension plugin (more accurate context from DOM vs screenshot)
- Simple dashboard: intervention history, mode statistics

---

## 10. Troubleshooting

### `'unknown entries (image)'` error

**Cause:** OpenClaw agent uses `image` tool but current model does not support vision.

**Fix:** Edit `openclaw.json` where OpenClaw runs:
```
tools.profile = "minimal"
```

### Telegram not reaching you

**Fix:** Edit `openclaw.json` where OpenClaw runs:
```
channels.telegram.allowFrom = ["*"],
channels.telegram.dmPolicy = "open"
```

### Agent slow or stuck

**Cause:** Too many webhook triggers per second.

**Fix:** Adjust `weruh.yaml`:
```yaml
capture:
  interval_seconds: 60
  change_threshold: 15
  active_hours: "09:00-18:00"
```

### Tesseract OCR not found

```
[X] OCR is enabled but Tesseract is not installed.
```

Install Tesseract OCR first:
```
Windows: choco install tesseract -y OR https://github.com/UB-Mannheim/tesseract/wiki
macOS:   brew install tesseract
Linux:   sudo apt install tesseract-ocr
```

---

## 11. Security & Privacy

### Core Principle: Data Never Leaves the Machine Without Explicit Permission

- Screenshots are **never stored permanently** — saved temporarily at `/tmp/weruh-frame.jpg` and deleted after processing
- **Primary path**: image is sent to the user's own OpenClaw gateway (local or private server) — no third party involved
- **Fallback path**: image is sent to the vision provider **explicitly configured by the user** — if left empty, the fallback is completely inactive. If using local Ollama as fallback, no data leaves the machine at all
- Vision provider API keys are stored in `weruh.yaml` with permission `600`, never logged
- Daemon can be paused at any time with `openweruh pause`
- Active hours restrict the operational window

### Threat Model

| Threat | Mitigation |
|---|---|
| Screenshot leaks to cloud | Primary path goes to user's own OpenClaw; cloud fallback only if user explicitly sets URL + API key |
| Untrusted vision provider | URL is fully controlled by the user — can be local Ollama, LAN, or any cloud of their choosing |
| Webhook token exposed | Token stored in file with permission `600`, not in env vars, never logged |
| Vision provider API key exposed | Stored in `weruh.yaml` with permission `600`, masked when displayed in CLI |
| False positive spam | `intervention_threshold` + cooldown per mode |
| Performance overhead | pHash filtering + configurable interval, vision call only when frame changes significantly |

---

## 12. Repository Structure

```
openweruh/
├── README.md
├── WHITEPAPER.md
├── LICENSE                         ← MIT
│
├── daemon/
│   ├── weruh.py                    ← main daemon entrypoint
│   ├── capture.py                  ← mss wrapper + pHash logic
│   ├── ocr.py                      ← OCR engine (pytesseract / easyocr)
│   ├── vision.py                   ← vision provider adapter (fallback LLM)
│   ├── trigger.py                  ← OpenClaw webhook sender
│   └── requirements.txt           ← mss, imagehash, httpx, pillow, pyyaml, pytesseract
│
├── skill/
│   └── openweruh/
│       ├── SKILL.md               ← agent instructions
│       └── references/
│           ├── modes.md           ← documentation per mode
│           └── examples.md        ← trigger & response examples
│
├── hook/
│   └── weruh-boot/
│       ├── HOOK.md                ← hook metadata
│       └── handler.ts             ← TypeScript hook handler
│
├── config/
│   └── weruh.example.yaml         ← configuration template
│
├── scripts/
│   ├── install.sh                 ← one-line installer
│   └── uninstall.sh
│
└── demo/
    └── README.md                  ← instructions for demo video
```

### Installation

```bash
# One-line install
curl -fsSL https://raw.githubusercontent.com/fikriaf/OpenWeruh/main/scripts/install.sh | bash

# Or manually
git clone https://github.com/fikriaf/OpenWeruh.git
cd OpenWeruh
pip install -r daemon/requirements.txt
cp config/weruh.example.yaml ~/.config/openweruh/weruh.yaml

# Register skill & hook with OpenClaw
npx clawhub install openweruh --no-input
openclaw hooks install hook/weruh-boot

# Start the daemon
python daemon/weruh.py start
```

---

## 13. Contributing & License

OpenWeruh is an open source project under the **MIT** license. Contributions are welcome for:

- Ports to new platforms (macOS GUI bridge)
- Additional persona modes
- Integration with new vision models
- Improvements to the change detection algorithm
- Documentation and demos

Skills published to ClawHub follow the **MIT-0** license per registry requirements.

---

## 14. References

### OpenClaw — Official Documentation (`docs.openclaw.ai`)

| Topic | URL | Relevance to OpenWeruh |
|---|---|---|
| Home / Overview | https://docs.openclaw.ai/ | General ecosystem overview |
| Configuration | https://docs.openclaw.ai/gateway/configuration | `hooks.enabled`, `hooks.token`, `hooks.path` — webhook foundation |
| Webhooks (Automation) | https://docs.openclaw.ai/automation/webhook | `/hooks/agent` endpoint, `sessionKey`, `allowRequestSessionKey` |
| Cron Jobs | https://docs.openclaw.ai/automation/cron-jobs.md | `isolated agentTurn`, `delivery.mode`, daily summary setup |
| Hooks (Agent Hooks) | https://docs.openclaw.ai/automation/hooks | `gateway:startup` lifecycle, hook discovery from `~/.openclaw/hooks/` |
| Skills | https://docs.openclaw.ai/tools/skills | SKILL.md format, YAML frontmatter, skill precedence, `alwaysActive` |
| Tools & Plugins | https://docs.openclaw.ai/tools | Built-in tools, screen record, nodes, image pipeline |
| Remote Access | https://docs.openclaw.ai/gateway/remote | SSH tunnel, Tailscale, `gateway.bind: loopback` — Mode B & C |
| Security | https://docs.openclaw.ai/gateway/security | Hook payload trust, token auth, credential storage |
| Agent Runtime | https://docs.openclaw.ai/concepts/agent | Session model, `wakeMode`, image pipeline behavior |
| Agent Workspace | https://docs.openclaw.ai/concepts/agent-workspace | `~/.openclaw/workspace/`, skills folder structure |
| Multi-Agent Routing | https://docs.openclaw.ai/concepts/multi-agent | Per-agent skills, shared skills in `~/.openclaw/skills/` |
| FAQ | https://docs.openclaw.ai/help/faq | Remote gateway access, tunnel setup, workspace migration |
| AGENTS.md Default | https://docs.openclaw.ai/reference/AGENTS.default | Peekaboo, screen recording, macOS permission context |

### OpenClaw — GitHub

| Repository | URL | Relevance |
|---|---|---|
| Main Repository | https://github.com/openclaw/openclaw | Source code, README, gateway architecture |
| AGENTS.md | https://github.com/openclaw/openclaw/blob/main/AGENTS.md | Doc conventions, official link format |
| Docker Image (coollabsio) | https://github.com/coollabsio/openclaw | `OPENCLAW_HOOKS_TOKEN`, `OPENCLAW_GATEWAY_TOKEN` env vars, Docker deploy |

### Vision Provider APIs

| Provider | URL | Relevance |
|---|---|---|
| Anthropic API Reference | https://docs.anthropic.com/en/api/messages | `x-api-key` format, `source.type: base64`, `anthropic-version` header |
| OpenAI Vision Guide | https://platform.openai.com/docs/guides/vision | `image_url` format, `data:image/jpeg;base64` |
| Google Gemini API | https://ai.google.dev/gemini-api/docs/vision | `inline_data` format, `x-goog-api-key`, per-model endpoint |
| OpenRouter Docs | https://openrouter.ai/docs/requests | OpenAI-compatible, multi-model routing |
| Ollama API | https://github.com/ollama/ollama/blob/main/docs/api.md | `/api/chat`, vision support (`llava`, `moondream2`) |
| Mistral API | https://docs.mistral.ai/api/ | OpenAI-compatible, `pixtral-large-latest` |
| Together AI Docs | https://docs.together.ai/docs/vision-overview | Vision models, Llama 3.2 Vision |
| xAI API | https://docs.x.ai/api | `grok-2-vision-latest`, OpenAI-compatible |

### Python Libraries (Daemon)

| Library | URL | Relevance |
|---|---|---|
| `mss` | https://python-mss.readthedocs.io/ | Cross-platform screen capture — core daemon |
| `imagehash` | https://github.com/JohannesBuchner/imagehash | pHash for change detection |
| `httpx` | https://www.python-httpx.org/ | HTTP client for webhook + vision API calls |
| `Pillow` | https://pillow.readthedocs.io/ | Image processing, format conversion |
| `pyyaml` | https://pyyaml.org/wiki/PyYAMLDocumentation | Parse `weruh.yaml` |

---

## Closing

OpenWeruh is not about surveillance — it is about giving an existing agent a new kind of intelligence: the ability to *weruh* (see and know) what is happening in front of the user, then wisely decide when to speak and when to stay silent.

This is the missing layer between the user's visual world and the intelligence OpenClaw already possesses.

---

*Version 0.1 — Draft for community discussion. Feedback welcome.*

*Built on research grounded in the actual OpenClaw ecosystem (ClawHub, docs.openclaw.ai, GitHub).*
