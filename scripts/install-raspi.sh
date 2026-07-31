#!/usr/bin/env bash
# Einmalig auf Raspberry Pi OS mit Desktop ausführen.
set -euo pipefail

REPO_URL="${1:?Aufruf: $0 <GitHub-Repository-URL> [Branch]}"
BRANCH="${2:-main}"
INSTALL_DIR="${SIGNAGE_DIR:-$HOME/voelk-digital-signage}"
SERVICE_USER="${SUDO_USER:-$USER}"

sudo apt-get update
sudo apt-get install -y git python3 python3-venv chromium-browser

if [[ -d "$INSTALL_DIR/.git" ]]; then
  git -C "$INSTALL_DIR" fetch --prune origin "$BRANCH"
  git -C "$INSTALL_DIR" checkout "$BRANCH"
  git -C "$INSTALL_DIR" reset --hard "origin/$BRANCH"
else
  git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$INSTALL_DIR"
fi

python3 -m venv "$INSTALL_DIR/.venv"
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

sudo install -m 644 "$INSTALL_DIR/deploy/signage.service" /etc/systemd/system/signage.service
sudo sed -i "s|__USER__|$SERVICE_USER|g; s|__INSTALL_DIR__|$INSTALL_DIR|g; s|__BRANCH__|$BRANCH|g" /etc/systemd/system/signage.service
sudo systemctl daemon-reload
sudo systemctl enable --now signage.service

mkdir -p "$HOME/.config/autostart"
sed "s|__START_URL__|http://127.0.0.1:8000/|g" "$INSTALL_DIR/deploy/signage-kiosk.desktop" > "$HOME/.config/autostart/signage-kiosk.desktop"
chmod 644 "$HOME/.config/autostart/signage-kiosk.desktop"

echo "Fertig. Nach dem nächsten Desktop-Login startet Chromium im Kiosk-Modus."
