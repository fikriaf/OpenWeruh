<div align="center">
  <img src="assets/logo_openweruh_github-readme.png" alt="OpenWeruh Logo" width="600" />

  <br />
  <br />

  **Proactive Screen-Aware Context Layer for OpenClaw**

  <br />

  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://openclaw.ai"><img src="https://img.shields.io/badge/Ecosystem-OpenClaw-FF4A00.svg?style=for-the-badge" alt="OpenClaw"></a>
  <a href="#"><img src="https://img.shields.io/badge/Status-Alpha-orange.svg?style=for-the-badge" alt="Status"></a>

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

<div align="center">
  <img src="assets/openweruh_flowchart.svg" alt="OpenWeruh Architecture Flowchart" width="400" />
</div>
<br/>

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

On the laptop/PC whose screen you wish to monitor, clone this repository first:

```bash
git clone https://github.com/fikriaf/OpenWeruh.git
cd OpenWeruh
```

#### Windows

1. Install Python dependencies:
   ```cmd
   pip install -r daemon\requirements.txt
   ```
2. Create the configuration directory and copy the template:
   ```cmd
   mkdir "%USERPROFILE%\.config\openweruh"
   copy config\weruh.example.yaml "%USERPROFILE%\.config\openweruh\weruh.yaml"
   ```
3. Copy the OpenClaw skill and hook manually to your OpenClaw directories:
   ```cmd
   xcopy /E /I skill\openweruh "%USERPROFILE%\.openclaw\skills\openweruh"
   xcopy /E /I hook\weruh-boot "%USERPROFILE%\.openclaw\hooks\weruh-boot"
   ```

#### Linux

1. Make the installation script executable:
   ```bash
   chmod +x scripts/*.sh
   ```
2. Run the installer script, which automatically handles dependencies and copies configuration files:
   ```bash
   ./scripts/install.sh
   ```

#### macOS

1. Make the installation script executable:
   ```bash
   chmod +x scripts/*.sh
   ```
2. Run the installer script:
   ```bash
   ./scripts/install.sh
   ```
*Note for macOS: You must explicitly grant "Screen Recording" permissions to your Terminal application (or the Python process running the daemon) in `System Settings > Privacy & Security > Screen Recording`.*

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

**Supported providers:**
<br/>
<div align="center">
  <img src="assets/openai_logo.svg" height="28" alt="OpenAI" />
  <img src="https://img.shields.io/badge/Anthropic-cc9c84?style=for-the-badge&logo=Anthropic&logoColor=black" alt="Anthropic" />
  <img src="https://img.shields.io/badge/Google_Gemini-8E75B2?style=for-the-badge&logo=Google%20Gemini&logoColor=white" alt="Google Gemini" />
  <img src="https://img.shields.io/badge/Ollama-FFFFFF?style=for-the-badge&logo=Ollama&logoColor=black" alt="Ollama" />
  <br/>
  <img src="assets/mistral_logo.svg" height="28" alt="Mistral AI" />
  <img src="https://img.shields.io/badge/OpenRouter-1A1A1A?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxZW0iIGhlaWdodD0iMWVtIiB2aWV3Qm94PSIwIDAgMjQgMjQiPjxnIGZpbGw9Im5vbmUiIHN0cm9rZT0iY3VycmVudENvbG9yIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiIHN0cm9rZS13aWR0aD0iMiI+PHJlY3Qgd2lkdGg9IjIwIiBoZWlnaHQ9IjgiIHg9IjIiIHk9IjE0IiByeD0iMiIvPjxwYXRoIGQ9Ik02LjAxIDE4SDZtNC4wMSAwSDEwbTUtOHY0bTIuODQtNi44M2E0IDQgMCAwIDAtNS42NiAwbTguNDgtMi44M2E4IDggMCAwIDAtMTEuMzEgMCIvPjwvZz48L3N2Zz4=&logoColor=white" alt="OpenRouter" />
  <img src="https://img.shields.io/badge/Together_AI-222222?style=for-the-badge&logo=data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiPz48c3ZnIGlkPSJMYXllcl8xIiBkYXRhLW5hbWU9IkxheWVyIDEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgdmlld0JveD0iMCAwIDQ4NC45OCA0NTIuNSI+PGRlZnM+PHN0eWxlPi5jbHMtMSB7ZmlsbDogI2VmMmNjMTt9LmNscy0yIHtmaWxsOiAjY2FhZWY1O30uY2xzLTMge2ZpbGw6ICNmYzRjMDI7fTwvc3R5bGU+PC9kZWZzPjxwYXRoIGNsYXNzPSJjbHMtMSIgZD0iTTQ2OC43Miw2MC42N0M0MzUuMjUsMi42OSwzNjEuMTEtMTcuMTgsMzAzLjEyLDE2LjNjLTM3LjMsMjEuNTQtNTguODIsNTkuNjItNjAuNTIsOTkuNjlsMTIxLjE1LjE2djEwLjM5aC0xMjEuMTVjLjc4LDE4Ljk0LDYuMDIsMzcuODEsMTYuMTUsNTUuMzYsMzMuNDgsNTcuOTgsMTA3LjYyLDc3Ljg1LDE2NS42LDQ0LjM3LDU3Ljk4LTMzLjQ4LDc3Ljg1LTEwNy42Miw0NC4zNy0xNjUuNloiLz48cGF0aCBjbGFzcz0iY2xzLTIiIGQ9Ik0xNi4yNiw2MC42M0MtMTcuMjEsMTE4LjYxLDIuNjUsMTkyLjc2LDYwLjYzLDIyNi4yM2MzNy4zLDIxLjU0LDgxLjA0LDIxLjEzLDExNi41OSwyLjU3bC02MC40NC0xMDUsOS01LjE4LDYwLjU3LDEwNC45MWMxNi4wMS0xMC4xNCwyOS43NC0yNC4xMiwzOS44Ny00MS42NywzMy40OC01Ny45OCwxMy42MS0xMzIuMTItNDQuMzctMTY1LjZDMTIzLjg4LTE3LjIxLDQ5Ljc0LDIuNjUsMTYuMjYsNjAuNjNaIi8+PHBhdGggY2xhc3M9ImNscy0zIiBkPSJNMjQyLjQ2LDQ1Mi41YzY2Ljk1LDAsMTIxLjIzLTU0LjI3LDEyMS4yMy0xMjEuMjMsMC00My4wNy0yMi4yMi04MC43NS01Ni4wNy0xMDIuMjVsLTYwLjcxLDEwNC44NC04Ljk5LTUuMjEsNjAuNTctMTA0LjkxYy0xNi43OS04Ljc5LTM1Ljc1LTEzLjctNTYuMDItMTMuNy02Ni45NSwwLTEyMS4yMyw1NC4yNy0xMjEuMjMsMTIxLjIzLDAsNjYuOTUsNTQuMjcsMTIxLjIzLDEyMS4yMywxMjEuMjNaIi8+PC9zdmc+&logoColor=white" alt="Together AI" />
  <img src="https://img.shields.io/badge/xAI-000000?style=for-the-badge&logo=x&logoColor=white" alt="xAI" />
  <img src="https://img.shields.io/badge/Custom_Proxy-444444?style=for-the-badge" alt="Custom" />
</div>

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
