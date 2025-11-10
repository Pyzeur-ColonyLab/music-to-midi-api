# MR-MT3 Deployment Guide

Complete guide for deploying the MR-MT3 music-to-MIDI API on an external server instance using nohup.

## Prerequisites

### Server Requirements
- **OS**: Ubuntu 20.04+ (or similar Linux)
- **RAM**: 16GB minimum (8GB works but slower)
- **CPU**: 4+ cores
- **Disk**: 20GB free space
- **Python**: 3.10+
- **Network**: Ports 8000 (API) and 22 (SSH)

### Local Requirements
- SSH access to server
- Git installed
- SCP or rsync for file transfer

## Deployment Steps

### 1. Initial Server Setup

```bash
# SSH into your server
ssh ubuntu@YOUR_SERVER_IP

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.10 and dependencies
sudo apt install -y python3.10 python3.10-venv python3-pip git

# Install system libraries
sudo apt install -y ffmpeg libsndfile1

# Create application directory
mkdir -p ~/music-to-midi-api
cd ~/music-to-midi-api
```

### 2. Clone Repository

```bash
# Clone from GitHub
git clone https://github.com/Pyzeur-ColonyLab/music-to-midi-api.git .

# Switch to MR-MT3 feature branch
git checkout feature/mr-mt3-integration

# Verify files
ls -la
```

### 3. Setup Python Environment

```bash
# Create virtual environment
python3.10 -m venv venv

# Activate environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install MR-MT3 dependencies
pip install -r requirements-mr-mt3.txt
```

**Expected installation time**: 5-10 minutes

### 4. Download MR-MT3 Model

```bash
# Make script executable
chmod +x scripts/setup_mr_mt3.sh

# Download model (~400MB)
./scripts/setup_mr_mt3.sh
```

This will:
- Create `models/mr-mt3/` directory
- Clone MR-MT3 repository
- Download model checkpoint
- Download configuration

**Verify model files**:
```bash
ls -lh models/mr-mt3/
# Should show:
# - mt3.pth (~400MB)
# - config.json (~2KB)
# - MR-MT3/ (repository)
```

### 5. Configure Environment

```bash
# Create .env file (optional)
cat > .env << EOF
# Server Configuration
PORT=8000
HOST=0.0.0.0

# MR-MT3 Configuration
USE_MR_MT3=1
MR_MT3_MODEL_PATH=./models/mr-mt3/mt3.pth
MR_MT3_CONFIG_PATH=./models/mr-mt3/config.json
MR_MT3_DEVICE=cuda  # or 'cpu' if no GPU

# API Configuration
MAX_UPLOAD_SIZE_MB=500
ALLOWED_ORIGINS=*

# Processing
MAX_CONCURRENT_JOBS=2
PROCESSING_TIMEOUT=600
EOF
```

### 6. Test Installation

```bash
# Activate virtual environment
source ~/music-to-midi-api/venv/bin/activate

# Test MR-MT3 service
python3 -c "
from app.services.mr_mt3_service import get_mr_mt3_service
service = get_mr_mt3_service()
print(service.get_model_info())
"

# Should output model info without errors
```

### 7. Start API with nohup

```bash
# Create logs directory
mkdir -p logs

# Start server in background with nohup
nohup python3 -m app.main > logs/api.log 2>&1 &

# Save process ID
echo $! > logs/api.pid

# Verify server is running
sleep 5
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","model_loaded":true,"device":"cuda"}
```

### 8. Management Commands

#### Check Server Status
```bash
# Check if process is running
cat logs/api.pid | xargs ps -p

# Check latest logs
tail -f logs/api.log

# Check health endpoint
curl http://localhost:8000/health
```

#### Stop Server
```bash
# Kill process using saved PID
kill $(cat logs/api.pid)

# Or find and kill by name
pkill -f "python3 -m app.main"

# Verify stopped
ps aux | grep "app.main"
```

#### Restart Server
```bash
# Stop server
kill $(cat logs/api.pid)

# Wait a moment
sleep 2

# Start server
cd ~/music-to-midi-api
source venv/bin/activate
nohup python3 -m app.main > logs/api.log 2>&1 &
echo $! > logs/api.pid
```

#### Update Code
```bash
# Stop server
kill $(cat logs/api.pid)

# Pull latest changes
git pull origin feature/mr-mt3-integration

# Reinstall dependencies (if needed)
source venv/bin/activate
pip install -r requirements-mr-mt3.txt

# Restart server
nohup python3 -m app.main > logs/api.log 2>&1 &
echo $! > logs/api.pid
```

### 9. Firewall Configuration

```bash
# Allow API port (8000)
sudo ufw allow 8000/tcp

# Verify firewall status
sudo ufw status
```

### 10. Test Deployment

```bash
# Test from server
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@test.mp3"

# Test from external machine
curl -X POST http://YOUR_SERVER_IP:8000/api/v1/upload \
  -F "file=@test.mp3"

# Check API documentation
curl http://YOUR_SERVER_IP:8000/docs
```

## Quick Start Script

Save this as `deploy.sh`:

```bash
#!/bin/bash
# MR-MT3 API Deployment Script

set -e

echo "🚀 Starting MR-MT3 API deployment..."

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

# 1. Setup environment
echo "📦 Setting up Python environment..."
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements-mr-mt3.txt

# 2. Download model
echo "📥 Downloading MR-MT3 model..."
chmod +x scripts/setup_mr_mt3.sh
./scripts/setup_mr_mt3.sh

# 3. Create logs directory
mkdir -p logs

# 4. Test installation
echo "🧪 Testing installation..."
python3 -c "from app.services.mr_mt3_service import get_mr_mt3_service; s = get_mr_mt3_service(); print('✅ Model loaded')"

# 5. Start server
echo "▶️  Starting API server..."
nohup python3 -m app.main > logs/api.log 2>&1 &
echo $! > logs/api.pid

# Wait for startup
sleep 5

# 6. Verify
echo "✅ Checking health..."
curl -s http://localhost:8000/health | python3 -m json.tool

echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo ""
echo "📊 Server running at: http://YOUR_SERVER_IP:8000"
echo "📖 API docs: http://YOUR_SERVER_IP:8000/docs"
echo "📝 Logs: tail -f logs/api.log"
echo "🛑 Stop: kill \$(cat logs/api.pid)"
```

Make executable and run:
```bash
chmod +x deploy.sh
./deploy.sh
```

## Monitoring

### View Real-time Logs
```bash
# Follow all logs
tail -f logs/api.log

# Filter errors only
tail -f logs/api.log | grep ERROR

# Last 100 lines
tail -n 100 logs/api.log
```

### Check Resource Usage
```bash
# Memory usage
free -h

# CPU usage
top -p $(cat logs/api.pid)

# Disk usage
df -h
```

### API Metrics
```bash
# Health check
curl http://localhost:8000/health

# Model info
curl http://localhost:8000/model/info

# System status
curl http://localhost:8000/
```

## Troubleshooting

### Server won't start

```bash
# Check logs
cat logs/api.log

# Verify Python environment
source venv/bin/activate
which python3

# Test model loading
python3 -c "from app.services.mr_mt3_service import get_mr_mt3_service; get_mr_mt3_service()"
```

### Port already in use

```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill process
sudo kill -9 $(sudo lsof -t -i:8000)
```

### Out of memory

```bash
# Check memory
free -h

# Reduce concurrent jobs in .env
MAX_CONCURRENT_JOBS=1

# Restart server
kill $(cat logs/api.pid)
nohup python3 -m app.main > logs/api.log 2>&1 &
```

### Model not found

```bash
# Verify model files
ls -lh models/mr-mt3/

# Re-download if missing
./scripts/setup_mr_mt3.sh
```

## Production Best Practices

### 1. Use Process Manager (Alternative to nohup)

Instead of nohup, consider using systemd:

```bash
# Create service file
sudo nano /etc/systemd/system/mr-mt3-api.service

# Add:
[Unit]
Description=MR-MT3 Music to MIDI API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/music-to-midi-api
Environment="PATH=/home/ubuntu/music-to-midi-api/venv/bin"
ExecStart=/home/ubuntu/music-to-midi-api/venv/bin/python3 -m app.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable mr-mt3-api
sudo systemctl start mr-mt3-api
sudo systemctl status mr-mt3-api
```

### 2. Setup Log Rotation

```bash
# Create logrotate config
sudo nano /etc/logrotate.d/mr-mt3-api

# Add:
/home/ubuntu/music-to-midi-api/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

### 3. Automatic Backups

```bash
# Backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=/home/ubuntu/backups
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf $BACKUP_DIR/mr-mt3-api-$DATE.tar.gz \
  --exclude='venv' \
  --exclude='models/mr-mt3/MR-MT3' \
  ~/music-to-midi-api
# Keep only last 7 backups
ls -t $BACKUP_DIR/mr-mt3-api-*.tar.gz | tail -n +8 | xargs rm -f
EOF

chmod +x backup.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/music-to-midi-api/backup.sh") | crontab -
```

## Performance Tuning

### For CPU-only servers
```bash
# Increase workers (if multi-core)
# Edit app/main.py or use environment variable
export UVICORN_WORKERS=4
```

### For GPU servers
```bash
# Verify GPU available
nvidia-smi

# Set device in .env
MR_MT3_DEVICE=cuda
```

## Security Considerations

1. **Firewall**: Only open necessary ports
2. **SSH**: Use key-based authentication
3. **Updates**: Regular system updates
4. **Monitoring**: Setup alerts for issues
5. **Backups**: Automated daily backups

## Support

- **Documentation**: See `MR_MT3_README.md` and `MR_MT3_MIGRATION.md`
- **Logs**: Check `logs/api.log` for errors
- **GitHub**: Open issues at repository

---

**Deployment Guide Version**: 1.0
**Last Updated**: 2025-11-10
**Assisted by**: Claude Code
