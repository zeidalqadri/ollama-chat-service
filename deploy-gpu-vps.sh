#!/bin/bash
# Deploy BORAK to GPU VPS (Ollama-only mode)
# Run this script ON the GPU VPS (192.168.0.251)

set -euo pipefail

echo "=== BORAK GPU VPS Deployment (Ollama-only) ==="
echo ""

# Phase 1: Clean up vLLM
echo "[1/5] Cleaning up vLLM processes..."
pkill -9 -f vllm 2>/dev/null || echo "  No vLLM processes found"
pkill -9 -f litellm 2>/dev/null || echo "  No LiteLLM processes found"

# Check GPU status
echo ""
echo "[2/5] GPU Status:"
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader

# Phase 2: Verify Ollama
echo ""
echo "[3/5] Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  Ollama is running. Available models:"
    curl -s http://localhost:11434/api/tags | jq -r '.models[].name' | sed 's/^/    - /'
else
    echo "  ERROR: Ollama is not running!"
    echo "  Start it with: systemctl start ollama"
    exit 1
fi

# Phase 3: Install systemd services
echo ""
echo "[4/5] Installing systemd services..."

# Create systemd directory if needed
sudo mkdir -p /etc/systemd/system

# Copy service files (assumes they're in current directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/systemd/borak.service" ]; then
    sudo cp "$SCRIPT_DIR/systemd/borak.service" /etc/systemd/system/
    echo "  Installed borak.service"
else
    echo "  WARNING: systemd/borak.service not found"
fi

if [ -f "$SCRIPT_DIR/systemd/cloudflared.service" ]; then
    sudo cp "$SCRIPT_DIR/systemd/cloudflared.service" /etc/systemd/system/
    echo "  Installed cloudflared.service"
else
    echo "  WARNING: systemd/cloudflared.service not found"
fi

sudo systemctl daemon-reload

# Phase 4: Start services
echo ""
echo "[5/5] Starting services..."

# Stop any existing BORAK process
pkill -f "uvicorn main:app" 2>/dev/null || true

# Enable and start services
sudo systemctl enable borak.service
sudo systemctl start borak.service
echo "  Started borak.service"

sudo systemctl enable cloudflared.service
sudo systemctl start cloudflared.service
echo "  Started cloudflared.service"

# Wait for services to start
sleep 3

# Verification
echo ""
echo "=== Verification ==="

echo ""
echo "Service Status:"
systemctl is-active borak.service && echo "  borak: running" || echo "  borak: NOT RUNNING"
systemctl is-active cloudflared.service && echo "  cloudflared: running" || echo "  cloudflared: NOT RUNNING"

echo ""
echo "Health Check (local):"
if curl -s http://localhost:8012/health > /dev/null 2>&1; then
    curl -s http://localhost:8012/health | jq
else
    echo "  WARNING: BORAK health check failed"
    echo "  Check logs: journalctl -u borak.service -n 50"
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Test URLs:"
echo "  Local:  http://192.168.0.251:8012"
echo "  Tunnel: https://borak.zeidgeist.com"
echo ""
echo "Useful commands:"
echo "  View logs:    journalctl -u borak.service -f"
echo "  Restart:      sudo systemctl restart borak.service"
echo "  Check tunnel: curl -s https://borak.zeidgeist.com/health"
