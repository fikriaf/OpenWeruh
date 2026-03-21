# OpenWeruh

**Proactive Screen-Aware Context Layer for OpenClaw**

> *Weruh* (Javanese) — to see, to know, to understand without being asked.

OpenWeruh bridges the gap between what you see on your screen and the OpenClaw agent, enabling truly proactive, context-aware assistance.

For a detailed technical overview, see the [Whitepaper](WHITEPAPER.md).

## Quick Start

1. Clone the repository
2. Run `./scripts/install.sh`
3. Edit `~/.config/openweruh/weruh.yaml`
4. Run `python daemon/weruh.py start`

## How it Works

OpenWeruh runs a lightweight local daemon that periodically captures your screen. If the screen changes significantly, it evaluates the context and securely sends it to your OpenClaw Gateway. Based on the selected **persona mode**, the agent decides if it should proactively notify you.

## License
MIT