<div align="center">
  <img src="assets/logo_openweruh_github-readme.png" alt="OpenWeruh Logo" width="600" />

  <br />
  <br />

  **Proactive Screen-Aware Context Layer for OpenClaw**

  <br />

  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
  [![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
  [![OpenClaw](https://img.shields.io/badge/Ecosystem-OpenClaw-FF4A00.svg)](https://openclaw.ai)
  [![Status](https://img.shields.io/badge/Status-Alpha-orange.svg)]()

  <br />

  > *Weruh* (Javanese) — to see, to know, to understand without being asked.
</div>

---

## Overview

OpenWeruh bridges the gap between real-time visual context on your screen and the intelligence of the OpenClaw agent ecosystem. It operates as a local background daemon that captures your screen, analyzes changes, and proactively sends relevant context to your OpenClaw Gateway. 

Instead of waiting for you to trigger a command, OpenWeruh allows the agent to observe your workflow and intervene intelligently based on configured persona modes.

For a comprehensive technical architecture and design philosophy, please refer to the [Whitepaper](WHITEPAPER.md).

---

## Core Features

*   **Real-Time Context**: Continuously monitors screen activity with minimal performance overhead using fast perceptual hashing (`pHash`).
*   **Persona Modes**: Configurable behavior profiles (`skeptic`, `researcher`, `focus`, `guardian`, `silent`) dictate how and when the agent intervenes.
*   **Privacy First**: All processing is local or sent securely to your own infrastructure. Screenshots are never permanently stored.
*   **Vision Provider Fallback**: If the OpenClaw Gateway lacks built-in vision support, OpenWeruh can seamlessly fall back to external APIs (OpenAI, Anthropic, Google Gemini, Ollama, etc.) to convert screen frames into text descriptions.

---

## Installation Guide (Remote Gateway Deployment)

This tutorial assumes you are running OpenClaw on a remote server (VPS) and working locally on a separate laptop or PC. 

### Prerequisites

*   **Server**: OpenClaw Gateway running and accessible via an endpoint (WebUI or API).
*   **Local Machine**: Python 3.8 or higher installed.

### 1. Server Configuration (OpenClaw)

First, enable the webhook interface on your OpenClaw server so it can receive context payloads from your local machine.

Run the following commands on your server:

```bash
openclaw config set hooks.enabled true
openclaw config set hooks.token "YOUR_SECURE_TOKEN"
openclaw restart
```

### 2. Local Setup (OpenWeruh Daemon)

On your local workstation, clone this repository and install the daemon components.

```bash
git clone https://github.com/fikriaf/OpenWeruh.git
cd OpenWeruh

# Execute the installation script
./scripts/install.sh
```

### 3. Client Configuration

The installation script creates a configuration file at `~/.config/openweruh/weruh.yaml`. Open this file and update the `gateway` settings to match your remote server.

```yaml
gateway:
  mode: "remote"
  url: "https://your-openclaw-server.com"
  hook_token: "YOUR_SECURE_TOKEN"
```

If your remote OpenClaw server does not process images reliably or lacks a configured vision model, you must configure a fallback vision provider in the same `weruh.yaml` file. For example, to use Google Gemini:

```yaml
vision:
  provider:
    type: "google"
    api_key: "YOUR_GEMINI_API_KEY"
    model: "gemini-2.5-flash"
```

### 4. Running the Daemon

Start the OpenWeruh background process on your local machine:

```bash
python daemon/weruh.py start
```

The daemon will now monitor your screen based on the interval configured in `weruh.yaml` (default: 15 seconds). When significant visual changes occur, context is transmitted to your OpenClaw server, allowing the agent to analyze the data and send proactive messages to your connected channels (e.g., Telegram).

---

## Directory Structure

```text
openweruh/
├── README.md                  # This file
├── WHITEPAPER.md              # Technical architecture documentation
├── LICENSE                    # MIT License
├── assets/                    # Static assets like logos
├── config/
│   └── weruh.example.yaml     # Configuration template
├── daemon/                    # Python background process
│   ├── capture.py             # Screen capture and hashing logic
│   ├── requirements.txt       # Daemon dependencies
│   ├── trigger.py             # Webhook transmission utility
│   ├── vision.py              # Fallback vision API integrations
│   └── weruh.py               # Main daemon entrypoint
├── demo/                      # Demonstration assets
├── hook/
│   └── weruh-boot/            # OpenClaw startup hook
├── scripts/
│   ├── install.sh             # Interactive installation script
│   └── uninstall.sh           # Removal script
└── skill/
    └── openweruh/             # OpenClaw Agent instructions
        ├── SKILL.md
        └── references/
```

---

## License

This project is open-source software distributed under the terms of the [MIT License](LICENSE).
