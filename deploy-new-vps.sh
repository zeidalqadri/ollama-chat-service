#!/bin/bash
# Migration script for Ollama Chat Service to new VPS
# Target: 192.168.0.251
# Run this script FROM your local machine

set -e

VPS_HOST="192.168.0.251"
VPS_PORT="22"  # Change to 1511 if needed
VPS_USER="the_bomb"
APP_DIR="/opt/ollama-ui"

echo "═══════════════════════════════════════════════════════════════"
echo "  OLLAMA CHAT SERVICE - VPS MIGRATION"
echo "  Target: $VPS_USER@$VPS_HOST:$VPS_PORT"
echo "═══════════════════════════════════════════════════════════════"

# Step 1: Test SSH connection
echo ""
echo "[1/6] Testing SSH connection..."
ssh -p $VPS_PORT -o ConnectTimeout=10 $VPS_USER@$VPS_HOST "echo 'SSH OK'" || {
    echo "ERROR: Cannot connect to VPS. Check:"
    echo "  - VPS is running"
    echo "  - SSH key is configured"
    echo "  - Correct port ($VPS_PORT)"
    exit 1
}

# Step 2: Install Ollama
echo ""
echo "[2/6] Installing Ollama on VPS..."
ssh -p $VPS_PORT $VPS_USER@$VPS_HOST 'curl -fsSL https://ollama.com/install.sh | sudo sh'

# Step 3: Start Ollama service
echo ""
echo "[3/6] Starting Ollama service..."
ssh -p $VPS_PORT $VPS_USER@$VPS_HOST 'sudo systemctl enable ollama && sudo systemctl start ollama'

# Step 4: Create app directory and install dependencies
echo ""
echo "[4/6] Setting up app directory and dependencies..."
ssh -p $VPS_PORT $VPS_USER@$VPS_HOST << 'REMOTE_SETUP'
sudo mkdir -p /opt/ollama-ui/static
sudo chown -R $USER:$USER /opt/ollama-ui
sudo apt-get update && sudo apt-get install -y python3-pip python3-venv
cd /opt/ollama-ui
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn python-jose[cryptography] passlib[bcrypt] httpx python-multipart chromadb bcrypt
REMOTE_SETUP

# Step 5: Copy app files
echo ""
echo "[5/6] Copying application files..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
scp -P $VPS_PORT "$SCRIPT_DIR/main.py" "$SCRIPT_DIR/sandbox.py" "$SCRIPT_DIR/requirements.txt" $VPS_USER@$VPS_HOST:$APP_DIR/
scp -P $VPS_PORT "$SCRIPT_DIR/static/"* $VPS_USER@$VPS_HOST:$APP_DIR/static/

# Step 6: Create systemd service
echo ""
echo "[6/6] Creating systemd service..."
ssh -p $VPS_PORT $VPS_USER@$VPS_HOST << 'SYSTEMD_SETUP'
sudo tee /etc/systemd/system/ollama-ui.service > /dev/null << 'EOF'
[Unit]
Description=Ollama Chat UI
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User=the_bomb
WorkingDirectory=/opt/ollama-ui
Environment="PATH=/opt/ollama-ui/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="SECRET_KEY=CHANGE_THIS_TO_SECURE_KEY"
ExecStart=/opt/ollama-ui/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8012
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ollama-ui
sudo systemctl start ollama-ui
SYSTEMD_SETUP

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  DEPLOYMENT COMPLETE!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  App URL: http://$VPS_HOST:8012"
echo ""
echo "  Next steps:"
echo "  1. SSH into VPS and pull models:"
echo "     ssh -p $VPS_PORT $VPS_USER@$VPS_HOST"
echo "     ollama pull qwen3-coder:30b  # Main coding model (18GB)"
echo ""
echo "  2. Generate a secure SECRET_KEY:"
echo "     python3 -c \"import secrets; print(secrets.token_hex(32))\""
echo "     Then edit /etc/systemd/system/ollama-ui.service"
echo ""
echo "  3. Check service status:"
echo "     systemctl status ollama-ui"
echo "     journalctl -u ollama-ui -f"
echo ""
