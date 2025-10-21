# Deployment Guide - Music-to-MIDI API

Complete manual deployment guide for production and development environments.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Local Development](#local-development)
3. [Production Deployment](#production-deployment)
4. [Server Platforms](#server-platforms)
5. [Troubleshooting](#troubleshooting)

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

## Server Platforms

### Recommended Providers

**Infomaniak (Recommended)**:
- Swiss cloud hosting with excellent privacy
- VPS instances from 8GB RAM
- Competitive pricing
- Good European network performance

**DigitalOcean**:
- **Size**: General Purpose, 8GB+ RAM
- **Image**: Ubuntu 22.04 LTS
- **Add-ons**: Backups recommended

**Other Compatible Providers**:
- Hetzner, OVH, Scaleway, Linode
- Any VPS provider supporting Ubuntu 22.04+
- Minimum 8GB RAM, 4 CPU cores recommended

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

### Typical VPS Costs

| Provider | vCPU | RAM | Storage | Cost/Month |
|----------|------|-----|---------|------------|
| Infomaniak | 4 | 8GB | 160GB | €15-25 |
| DigitalOcean | 4 | 8GB | 160GB | $48 |
| Hetzner | 4 | 16GB | 160GB | €20 |

*Prices approximate and subject to change*

---

## Support

- **Documentation**: See [README.md](README.md)
- **Issues**: GitHub Issues
- **API Docs**: http://localhost:8000/docs

---

**Last Updated**: October 2025
