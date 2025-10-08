#!/bin/bash
set -e

echo "============================================================"
echo "🚀 Music-to-MIDI API - Automated Setup"
echo "============================================================"

# Detect architecture
ARCH=$(uname -m)
echo "📋 System: $(uname -s) $ARCH"

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Warning: Running as root. Consider using a non-root user."
fi

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3.10 \
    python3-pip \
    python3-venv \
    ffmpeg \
    git \
    build-essential

echo "✅ System dependencies installed"

# Setup repository
REPO_DIR="$HOME/music-to-midi-api"
echo ""
echo "📂 Setting up repository..."

if [ -d "$REPO_DIR" ]; then
    echo "   Repository exists, pulling latest changes..."
    cd "$REPO_DIR" && git pull
else
    echo "   Cloning repository..."
    git clone https://github.com/Pyzeur-ColonyLab/music-to-midi-api.git "$REPO_DIR"
    cd "$REPO_DIR"
fi

echo "✅ Repository ready at $REPO_DIR"

# Create virtual environment
echo ""
echo "🐍 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "✅ Virtual environment created"

# Install Python dependencies
echo ""
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Dependencies installed"

# Download models (if script exists)
echo ""
echo "🤖 Checking for pre-trained models..."
if [ -f "scripts/download_models.py" ]; then
    echo "   Downloading models (this may take a while)..."
    python scripts/download_models.py
    echo "✅ Models downloaded"
else
    echo "⚠️  Model download script not found"
    echo "   Please ensure 3-stem models are in app/models/3_stems_models/"
fi

# Create necessary directories
echo ""
echo "📁 Creating application directories..."
mkdir -p uploads
mkdir -p logs
echo "✅ Directories created"

# Setup systemd service
echo ""
echo "⚙️  Setting up systemd service..."

SERVICE_FILE="/etc/systemd/system/music-to-midi-api.service"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Music-to-MIDI API Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$REPO_DIR
Environment="PATH=$REPO_DIR/venv/bin"
ExecStart=$REPO_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

# Logging
StandardOutput=append:$REPO_DIR/logs/service.log
StandardError=append:$REPO_DIR/logs/error.log

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Systemd service configuration created"

# Enable and start service
echo ""
echo "🔄 Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable music-to-midi-api
sudo systemctl start music-to-midi-api

echo "✅ Service enabled and started"

# Check service status
echo ""
echo "📊 Service status:"
sudo systemctl status music-to-midi-api --no-pager || true

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "============================================================"
echo "✅ Setup Complete!"
echo "============================================================"
echo ""
echo "📋 Service Management:"
echo "   Status:  sudo systemctl status music-to-midi-api"
echo "   Logs:    sudo journalctl -u music-to-midi-api -f"
echo "   Restart: sudo systemctl restart music-to-midi-api"
echo "   Stop:    sudo systemctl stop music-to-midi-api"
echo ""
echo "🌐 API Endpoints:"
echo "   Local:       http://localhost:8000"
echo "   Network:     http://$SERVER_IP:8000"
echo "   Docs:        http://$SERVER_IP:8000/docs"
echo "   Health:      http://$SERVER_IP:8000/health"
echo ""
echo "📁 Application Directory: $REPO_DIR"
echo "📝 Service Logs: $REPO_DIR/logs/"
echo ""
echo "🚀 Ready to transcribe audio to MIDI!"
echo "============================================================"
