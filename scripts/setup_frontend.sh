#!/usr/bin/env bash
# Setup script for BirdNET-Pi new frontend + API server
set -e

source /etc/birdnet/birdnet.conf
BIRDNET_HOME=$(getent passwd "${BIRDNET_USER}" | cut -d: -f6)

BIRDNET_DIR="${BIRDNET_HOME}/BirdNET-Pi"
VENV="$BIRDNET_DIR/birdnet"

echo "=== BirdNET-Pi Frontend Setup ==="
echo ""

# 1. Install Python dependencies
echo "[1/4] Installing Python dependencies..."
"$VENV/bin/pip" install --quiet fastapi==0.115.12 "uvicorn[standard]==0.34.2"
echo "  Done."

# 2. Install the systemd service
echo "[2/4] Setting up API service..."
sed "s|BIRDNET_USER_PLACEHOLDER|${BIRDNET_USER}|g; s|HOME_PLACEHOLDER|${BIRDNET_HOME}|g" \
  "$BIRDNET_DIR/templates/birdnet_api.service" \
  | sudo tee /etc/systemd/system/birdnet_api.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable birdnet_api
sudo systemctl restart birdnet_api
echo "  Done."

# 3. Update Caddy configuration
echo "[3/4] Updating Caddy configuration..."
sudo "$BIRDNET_DIR/scripts/update_caddyfile.sh"
echo "  Done."

# 4. Verify
echo "[4/4] Verifying..."
sleep 2

if curl -sf http://localhost:7007/api/v2/summary > /dev/null 2>&1; then
  echo "  API server: OK"
else
  echo "  API server: FAILED (check with: sudo systemctl status birdnet_api)"
fi

if curl -sf http://localhost/ > /dev/null 2>&1; then
  echo "  Frontend:   OK"
else
  echo "  Frontend:   FAILED (check with: sudo systemctl status caddy)"
fi

echo ""
echo "=== Setup complete ==="
echo "Visit http://$(hostname -I | awk '{print $1}')/ to see the new interface."
echo ""
echo "To rollback:"
echo "  sudo systemctl stop birdnet_api"
echo "  sudo cp /etc/caddy/Caddyfile.original /etc/caddy/Caddyfile"
echo "  sudo systemctl reload caddy"
