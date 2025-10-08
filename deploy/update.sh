#!/bin/bash
set -e

echo "============================================================"
echo "🔄 Music-to-MIDI API - Quick Update"
echo "============================================================"

# Navigate to repository
REPO_DIR="$HOME/music-to-midi-api"

if [ ! -d "$REPO_DIR" ]; then
    echo "❌ Repository not found at $REPO_DIR"
    echo "   Run setup.sh first"
    exit 1
fi

cd "$REPO_DIR"

# Pull latest changes
echo ""
echo "📥 Pulling latest changes from GitHub..."
git pull

# Activate virtual environment
echo ""
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Update dependencies (if requirements.txt changed)
echo ""
echo "📚 Checking for dependency updates..."
pip install --upgrade pip
pip install -r requirements.txt

# Restart service
echo ""
echo "🔄 Restarting service..."
sudo systemctl restart music-to-midi-api

# Wait for service to start
sleep 2

# Check status
echo ""
echo "📊 Service status:"
sudo systemctl status music-to-midi-api --no-pager || true

echo ""
echo "============================================================"
echo "✅ Update Complete!"
echo "============================================================"
echo ""
echo "📋 Useful Commands:"
echo "   View logs:   sudo journalctl -u music-to-midi-api -f"
echo "   Check status: sudo systemctl status music-to-midi-api"
echo ""
echo "🌐 API available at: http://$(hostname -I | awk '{print $1}'):8000"
echo "============================================================"
