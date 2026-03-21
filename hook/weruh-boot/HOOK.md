---
name: weruh-boot
description: Inject OpenWeruh screen context capability at gateway startup
events:
  - gateway:startup
version: 1.0.0
---

This hook registers the OpenWeruh screen context layer every time the OpenClaw Gateway starts up, alerting the agent that the `screen.context` tool is active.