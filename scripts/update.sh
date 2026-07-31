#!/usr/bin/env bash
# Aktualisiert die Installation auf den Stand des konfigurierten Git-Branches.
set -euo pipefail

INSTALL_DIR="${SIGNAGE_DIR:-$HOME/voelk-digital-signage}"
BRANCH="${SIGNAGE_BRANCH:-main}"

cd "$INSTALL_DIR"
if git fetch --prune origin "$BRANCH"; then
  # Der Pi ist ein Deployment-Ziel; lokale Änderungen werden durch GitHub ersetzt.
  git reset --hard "origin/$BRANCH"
else
  echo "GitHub nicht erreichbar; starte mit dem bereits installierten Stand." >&2
fi

if [[ -x .venv/bin/pip ]]; then
  .venv/bin/pip install --quiet -r requirements.txt || \
    echo "Python-Abhängigkeiten konnten nicht aktualisiert werden; nutze vorhandene Pakete." >&2
fi
