#!/usr/bin/env bash
# Sets up Plane Portal to run as a systemd service on Raspberry Pi.
# Run once as the user who should own the service:
#   bash setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
SERVICE_NAME="planeportal"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
CURRENT_USER="$(whoami)"

echo "==> Plane Portal setup"
echo "    Install path : $SCRIPT_DIR"
echo "    Running as   : $CURRENT_USER"
echo

# ── 1. Create / update virtual environment ───────────────────────────────────
echo "==> Creating virtual environment..."
python3 -m venv "$VENV_DIR"

echo "==> Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo "    Done."
echo

# ── 2. Ensure settings.toml exists ───────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/settings.toml" ]; then
    cp "$SCRIPT_DIR/settings.toml.example" "$SCRIPT_DIR/settings.toml"
    echo "==> Created settings.toml from example."
    echo "    Edit $SCRIPT_DIR/settings.toml before starting the service."
    echo
fi

# ── 3. Install systemd service ───────────────────────────────────────────────
echo "==> Installing systemd service (requires sudo)..."

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Plane Portal
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=${VENV_DIR}/bin/python ${SCRIPT_DIR}/code.py
Restart=on-failure
RestartSec=15

# Uncomment the line below if running without a desktop (direct framebuffer).
# Environment=SDL_VIDEODRIVER=fbdev SDL_FBDEV=/dev/fb0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
echo "    Service installed and enabled."
echo

# ── 4. Done ──────────────────────────────────────────────────────────────────
echo "==> Setup complete."
echo
echo "    Start now  : sudo systemctl start $SERVICE_NAME"
echo "    Stop       : sudo systemctl stop $SERVICE_NAME"
echo "    View logs  : journalctl -u $SERVICE_NAME -f"
echo
echo "    Make sure settings.toml has your coordinates before starting."
