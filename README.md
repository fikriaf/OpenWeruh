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

## Table of Contents

- [Overview](#overview)
- [The Problem It Solves](#the-problem-it-solves)
- [System Architecture](#system-architecture)
- [Core Features](#core-features)
- [Persona Modes](#persona-modes)
- [Deployment Topologies](#deployment-topologies)
- [Installation Guide (Remote Server / VPS)](#installation-guide-remote-server--vps)
- [Configuration](#configuration)
- [Vision Provider Fallback](#vision-provider-fallback)
- [Security & Privacy](#security--privacy)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview

**OpenWeruh** is an underlying context layer for the [OpenClaw](https://openclaw.ai) ecosystem. It bridges the gap between the real-time visual context on your screen and the existing intelligence of the OpenClaw agent.

Instead of waiting for you to trigger a command or depending strictly on time-based crons, OpenWeruh allows the agent to observe your workflow and intervene intelligently based on configured persona modes. If you are staring at a bug, reading a controversial claim, or deviating from your goals, OpenWeruh securely feeds that context to your agent.

For an in-depth understanding of the design philosophy, refer to the [Whitepaper v0.1](WHITEPAPER.md).

---

## The Problem It Solves

1.  **Blind Agents**: Standard AI agents can read files and APIs, but they cannot see what you are currently doing on your screen.
2.  **Reactive vs. Proactive**: Most "screen capture" skills require you to explicitly type *"take a screenshot"*. This is reactive. OpenWeruh runs in the background and speaks up only when necessary.
3.  **OS Permissions**: Running headless daemons that need screen capture permissions (especially on macOS) is highly problematic. OpenWeruh separates the capture daemon from the main OpenClaw Gateway to solve this natively.

---

## System Architecture

OpenWeruh consists of four decoupled components:

1.  **Python Screen Daemon (`daemon/`)**: Captures the screen, applies perceptual hashing (`pHash`) to detect meaningful changes, and securely dispatches the data via Webhooks.
2.  **OpenClaw Skill (`skill/`)**: Instructs the OpenClaw agent on how to react to screen context payloads using defined "Persona Modes."
3.  **Startup Hook (`hook/`)**: Injects the `screen.context` capability into the agent's awareness during the `gateway:startup` event.
4.  **Configuration (`config/`)**: A dedicated `weruh.yaml` file to control sensitivity, active hours, and vision fallbacks.

---

## Core Features

*   **Change Detection (`pHash`)**: Ensures the agent is only called when significant visual changes occur, minimizing API costs and performance overhead.
*   **Decoupled Operation**: Does not conflict with existing OpenClaw skills or crons.
*   **Vision Provider Fallback**: If OpenClaw's internal image pipeline drops the frame or lacks a configured vision model, OpenWeruh automatically falls back to OpenAI, Anthropic, Google Gemini, Ollama, or custom providers.

---

## Persona Modes

OpenWeruh's value lies in its intelligent filtering. The agent adopts a specific persona depending on your needs:

| Mode | Behavior |
| :--- | :--- |
| **`skeptic`** | Scrutinizes news, claims, or facts for bias. Actively searches for counter-arguments and presents them. |
| **`researcher`** | Observes technical reading and automatically provides supporting definitions, related papers, or context. |
| **`focus`** | Monitors activity against a declared session goal. Intervenes if you deviate (e.g., browsing social media while coding). |
| **`guardian`** | Tracks idle time or prolonged usage of distracting applications, gently reminding you to take breaks. |
| **`silent`** | Background recording only. No proactive notifications. Ideal for generating end-of-day activity summaries. |

---

## Deployment Topologies

OpenWeruh supports three deployment architectures:

1.  **Mode A (Local)**: OpenClaw Gateway and the OpenWeruh daemon run on the exact same local machine.
2.  **Mode B (SSH Tunnel)**: OpenClaw runs on a remote VPS, but is bound to `loopback`. You use an SSH tunnel (`autossh`) to securely link the local daemon to the server. *(Recommended for high privacy)*.
3.  **Mode C (Remote Public URL)**: OpenClaw runs on a remote server accessible via Tailscale, Localtonet, or a standard Reverse Proxy (Nginx/Caddy). The daemon transmits via HTTPS.

---

## Installation Guide (Remote Server / VPS)

*The following guide assumes **Mode C** (or Mode B with a mapped port) where OpenClaw is running remotely and your workstation is local.*

### Step 1: Server Configuration (OpenClaw)

Enable the webhook interface on your OpenClaw server. Connect to your VPS and run:

```bash
openclaw config set hooks.enabled true
openclaw config set hooks.token "YOUR_SECURE_TOKEN"
openclaw restart
```
*(Keep this token safe; it authenticates the incoming images).*

### Step 2: Local Installation (Workstation)

On the laptop/PC whose screen you wish to monitor, clone this repository and install the dependencies:

```bash
git clone https://github.com/fikriaf/OpenWeruh.git
cd OpenWeruh

# Make scripts executable (Linux/macOS)
chmod +x scripts/*.sh

# Run the installer
./scripts/install.sh
```

*Note for Windows users: Simply run `pip install -r daemon/requirements.txt`, then manually copy `config/weruh.example.yaml` to `C:\Users\YourUser\.config\openweruh\weruh.yaml`.*

### Step 3: Configure the Daemon

Edit the generated configuration file located at `~/.config/openweruh/weruh.yaml`.

```yaml
gateway:
  mode: "remote"
  url: "https://your-openclaw-endpoint.com"  # e.g., https://claw.yourdomain.com
  hook_token: "YOUR_SECURE_TOKEN"

capture:
  interval_seconds: 15
  change_threshold: 10
  active_hours: "07:00-23:00"

persona:
  mode: "guardian"
  language: "en"
```

### Step 4: Run the Daemon

```bash
python daemon/weruh.py start
```

---

## Vision Provider Fallback

If your OpenClaw server's `imageModel` is not configured correctly, or you are experiencing pipeline drops, OpenWeruh includes an internal Vision Adapter.

By defining a fallback provider in `weruh.yaml`, the daemon will process the image locally into a text description *before* sending it to the OpenClaw webhook.

Example for **Google Gemini**:
```yaml
vision:
  provider:
    type: "google"
    api_key: "AIzaSy..."
    model: "gemini-2.5-flash"
```

Example for **Ollama (Fully Local)**:
```yaml
vision:
  provider:
    type: "ollama"
    url: "http://localhost:11434/api/chat"
    model: "llava:13b"
```

*Supported providers: `openai`, `anthropic`, `google`, `ollama`, `openrouter`, `mistral`, `together`, `xai`, `custom`.*

---

## Security & Privacy

Data never leaves your machine without explicit permission.

*   **No Permanent Storage**: Screenshots are temporarily saved to `/tmp/weruh-frame.jpg` and immediately overwritten.
*   **Direct Transmission**: In the primary path, images are sent directly to your own OpenClaw gateway. No third-party servers are involved.
*   **Safeguards**: Active hours prevent capturing during personal time, and the change threshold prevents capturing highly repetitive frames. API keys are stored locally with `600` permissions.

---

## Roadmap

- [x] **v0.1**: Foundation (Python daemon, pHash detection, SKILL.md, Webhook integration).
- [ ] **v0.2**: Vision Intelligence enhancements (Multi-provider fallback support integration, daily summary crons).
- [ ] **v0.3**: Advanced Context (Session goals, browser extensions for DOM context, history dashboard).

---

## Author

**Fikri Armia Fahmi (FikriAF)**

*   **Email**: [fikriarmia27@gmail.com](mailto:fikriarmia27@gmail.com)
*   **LinkedIn**: [Fikri Armia Fahmi](https://www.linkedin.com/in/fikri-armia-fahmi-b373b3288/)
*   **Website**: [faftech.net](https://faftech.net)

---

## License

This project is licensed under the [MIT License](LICENSE).
