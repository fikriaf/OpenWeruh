#!/usr/bin/env bash
set -e

echo "OpenWeruh Installer"
echo "==================="

# Directories
CONFIG_DIR="$HOME/.config/openweruh"
SKILL_DIR="$HOME/.openclaw/skills/openweruh"
HOOK_DIR="$HOME/.openclaw/hooks/weruh-boot"

# Check if repo is cloned
if [ ! -f "daemon/weruh.py" ]; then
    echo "Error: Please run this script from the openweruh repository root."
    exit 1
fi

echo "1. Installing Python dependencies..."
pip install -r daemon/requirements.txt

echo "2. Setting up config directory..."
mkdir -p "$CONFIG_DIR"
if [ ! -f "$CONFIG_DIR/weruh.yaml" ]; then
    cp config/weruh.example.yaml "$CONFIG_DIR/weruh.yaml"
    chmod 600 "$CONFIG_DIR/weruh.yaml"
    echo "Created config at $CONFIG_DIR/weruh.yaml. Please edit before running."
fi

echo "3. Installing OpenClaw components..."
mkdir -p "$HOME/.openclaw/skills"
mkdir -p "$HOME/.openclaw/hooks"
cp -r skill/openweruh "$HOME/.openclaw/skills/"
cp -r hook/weruh-boot "$HOME/.openclaw/hooks/"

echo ""
echo "Installation complete!"
echo "Run the setup via: python daemon/weruh.py setup"
echo "Start the daemon via: python daemon/weruh.py start"
echo ""
echo "Optional: Add a daily summary cron job via OpenClaw CLI:"
echo "openclaw cron add --name \"weruh-daily-summary\" --cron \"0 21 * * *\" --session isolated --message \"Summarize today's screen context observations from weruh session.\" --announce --channel last"