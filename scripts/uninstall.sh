#!/usr/bin/env bash

echo "OpenWeruh Uninstaller"
echo "====================="

CONFIG_DIR="$HOME/.config/openweruh"
SKILL_DIR="$HOME/.openclaw/skills/openweruh"
HOOK_DIR="$HOME/.openclaw/hooks/weruh-boot"

read -p "Are you sure you want to remove OpenWeruh? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Removing config..."
    rm -rf "$CONFIG_DIR"
    
    echo "Removing OpenClaw skill..."
    rm -rf "$SKILL_DIR"
    
    echo "Removing OpenClaw hook..."
    rm -rf "$HOOK_DIR"
    
    echo "OpenWeruh components removed."
fi