#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
SERVICE_FILE="$SERVICE_DIR/copilot.service"

mkdir -p "$SERVICE_DIR"
sed "s|%h/Boot-to-Browser|$PROJECT_DIR|g" "$PROJECT_DIR/startup/copilot.service" > "$SERVICE_FILE"

systemctl --user daemon-reload
systemctl --user enable --now copilot.service

printf 'Installed and started %s\n' "$SERVICE_FILE"
