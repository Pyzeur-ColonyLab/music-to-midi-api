# Deployment Guide - Music-to-MIDI API

Complete deployment guide for production and development environments.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Cloud Platforms](#cloud-platforms)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- Python 3.9+
- 8GB+ RAM (16GB recommended)
- 10GB+ disk space
- (Optional) NVIDIA GPU with CUDA support

### Installation

```bash
# 1. Clone repository
git clone <your-repo-url>
cd music-to-midi-api

# 2. Download YourMT3 checkpoint
./setup_checkpoint.sh

# 3. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start server
python -m app.main
```

Server will be available at `http://localhost:8000`

---

## Local Development

### Setup

```bash
# Install in development mode
pip install -r requirements.txt

# Run with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing Without Model

For fast startup during development:

```bash
SKIP_MODEL_LOADING=1 python -m app.main
```

This starts the API without loading YourMT3 (useful for testing API structure).

### Running Tests

```bash
# Verification test
python test_local_amt.py

# Full sanity test
python sanity_test.py

# Run pytest suite
pytest tests/
```

---

## Docker Deployment

### Build and Run

```bash
# 1. Download checkpoint first
./setup_checkpoint.sh

# 2. Build image
docker build -t music-to-midi-api .

# 3. Run container
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/amt:/app/amt \
  --name music-to-midi-api \
  music-to-midi-api
```

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Docker Compose with GPU

Uncomment GPU section in `docker-compose.yml`:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

---

## Production Deployment

### Environment Variables

Create `.env` file:

```bash
# Server configuration
PORT=8000
HOST=0.0.0.0
WORKERS=1  # Increase for production (1 worker per 2GB RAM)

# Model configuration
SKIP_MODEL_LOADING=0

# Security
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Performance
MAX_UPLOAD_SIZE=100  # MB
REQUEST_TIMEOUT=600  # seconds (10 minutes)
```

### Production Server (Gunicorn)

```bash
# Install Gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn app.main:app \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 600 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts for long-running requests
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }
}
```

### SSL/TLS (Certbot)

```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com
```

---

## Cloud Platforms

### AWS EC2

**Instance Requirements**:
- **CPU**: t3.xlarge (4 vCPU, 16GB RAM) or larger
- **GPU** (optional): p3.2xlarge (1x NVIDIA V100, 61GB RAM)
- **Storage**: 20GB+ EBS volume

**Setup**:

```bash
# 1. SSH into instance
ssh -i your-key.pem ubuntu@your-instance-ip

# 2. Install dependencies
sudo apt-get update
sudo apt-get install -y python3.9 python3-pip ffmpeg libsndfile1 nginx

# 3. Clone and setup
git clone <your-repo-url>
cd music-to-midi-api
./setup_checkpoint.sh
pip install -r requirements.txt

# 4. Setup systemd service
sudo cp deployment/music-to-midi-api.service /etc/systemd/system/
sudo systemctl enable music-to-midi-api
sudo systemctl start music-to-midi-api
```

### Google Cloud Platform (GCP)

**Compute Engine**:

```bash
# Create instance with GPU
gcloud compute instances create music-to-midi-api \
  --zone=us-central1-a \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --boot-disk-size=50GB \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud

# Install CUDA drivers (if using GPU)
gcloud compute ssh music-to-midi-api --zone=us-central1-a
sudo /opt/deeplearning/install-driver.sh
```

### Azure

**Virtual Machine**:

```bash
# Create VM
az vm create \
  --resource-group myResourceGroup \
  --name music-to-midi-api \
  --image UbuntuLTS \
  --size Standard_NC6 \
  --generate-ssh-keys

# Open port 8000
az vm open-port --port 8000 --resource-group myResourceGroup --name music-to-midi-api
```

### DigitalOcean

**Droplet**:
- **Size**: General Purpose, 4GB+ RAM ($24/month)
- **Image**: Ubuntu 22.04 LTS
- **Add-ons**: Backups recommended

### Heroku

**Not Recommended** due to:
- 512MB RAM limit (too low for YourMT3)
- 30-second request timeout (too short for processing)
- No GPU support

---

## Performance Optimization

### CPU Optimization

```bash
# Increase workers for better throughput
WORKERS=4 gunicorn app.main:app --worker-class uvicorn.workers.UvicornWorker

# Set thread limits
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
```

### GPU Optimization

```python
# Automatic GPU detection (already implemented)
device = "cuda" if torch.cuda.is_available() else "cpu"
```

Verify GPU usage:

```bash
# Monitor GPU
nvidia-smi -l 1

# Check PyTorch GPU access
python -c "import torch; print(torch.cuda.is_available())"
```

### Memory Management

```bash
# Monitor memory
watch -n 1 free -h

# Limit model instances
# Currently using singleton pattern (efficient)
```

---

## Monitoring

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed status
curl http://localhost:8000/model/info
```

### Logging

```python
# Logs location
logs/
├── access.log  # Request logs
├── error.log   # Error logs
└── app.log     # Application logs
```

View logs:

```bash
# Tail logs
tail -f logs/app.log

# Search for errors
grep ERROR logs/error.log
```

### Prometheus Metrics (Optional)

Install prometheus client:

```bash
pip install prometheus-fastapi-instrumentator
```

Add to `app/main.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

---

## Security

### API Key Authentication (Recommended for Production)

Add to `app/api/middleware.py`:

```python
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY", "your-secret-key")
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
```

### Rate Limiting

```bash
pip install slowapi
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/v1/upload")
@limiter.limit("10/minute")
async def upload_endpoint(request: Request):
    ...
```

### File Upload Security

Already implemented:
- Filename sanitization (path traversal protection)
- File type validation
- Size limits

---

## Scaling

### Horizontal Scaling

**Load Balancer** (Nginx):

```nginx
upstream api_backend {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

server {
    location / {
        proxy_pass http://api_backend;
    }
}
```

Start multiple instances:

```bash
# Instance 1
gunicorn app.main:app --bind 0.0.0.0:8000

# Instance 2
gunicorn app.main:app --bind 0.0.0.0:8001

# Instance 3
gunicorn app.main:app --bind 0.0.0.0:8002
```

### Queue System (Redis + Celery)

For async processing:

```bash
pip install celery redis
```

---

## Backup & Recovery

### Data Backup

```bash
# Backup uploads
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/

# Backup logs
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/
```

### Checkpoint Backup

```bash
# Backup checkpoint (large file)
tar -czf amt_backup.tar.gz amt/
```

---

## Troubleshooting

### Model Won't Load

```bash
# Check checkpoint exists
ls -lh amt/logs/2024/.../checkpoints/last.ckpt

# Run verification
python test_local_amt.py

# Check logs
tail -f logs/error.log
```

### Out of Memory

```bash
# Reduce workers
WORKERS=1 gunicorn ...

# Monitor memory
watch -n 1 free -h

# Kill process if stuck
pkill -f "uvicorn app.main"
```

### Slow Processing

```bash
# Check if using GPU
python -c "import torch; print(torch.cuda.is_available())"

# Monitor CPU
htop

# Check disk I/O
iotop
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

---

## Cost Estimation

### AWS EC2

| Instance Type | vCPU | RAM | GPU | Cost/Hour | Cost/Month |
|--------------|------|-----|-----|-----------|------------|
| t3.xlarge | 4 | 16GB | - | $0.17 | ~$120 |
| p3.2xlarge | 8 | 61GB | 1x V100 | $3.06 | ~$2,200 |

### GCP Compute Engine

| Machine Type | vCPU | RAM | GPU | Cost/Hour | Cost/Month |
|-------------|------|-----|-----|-----------|------------|
| n1-standard-4 | 4 | 15GB | - | $0.19 | ~$140 |
| n1-standard-4 + T4 | 4 | 15GB | 1x T4 | $0.54 | ~$390 |

### DigitalOcean

| Droplet Size | vCPU | RAM | Cost/Month |
|-------------|------|-----|------------|
| General Purpose | 4 | 8GB | $48 |
| General Purpose | 4 | 16GB | $96 |

---

## Support

- **Documentation**: See [README.md](README.md)
- **Issues**: GitHub Issues
- **API Docs**: http://localhost:8000/docs

---

**Last Updated**: October 2025
