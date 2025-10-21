# Music-to-MIDI API

AI-powered audio-to-MIDI transcription service using YourMT3 and Demucs for professional music production.

[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Overview

Transform audio files into MIDI with high accuracy using state-of-the-art deep learning models:

- **YourMT3**: Advanced audio-to-MIDI transcription (536M parameters)
- **Demucs**: Professional stem separation (bass, drums, other, vocals)
- **FastAPI**: Production-ready REST API with async processing

### Features

✨ **Multi-Stem Processing**
- Automatic 4-stem separation (bass, drums, other, vocals)
- Independent MIDI generation per stem
- General MIDI (GM) instrument program assignment

🎯 **High Accuracy**
- YourMT3 YPTF.MoE+Multi model
- Multi-instrument polyphonic transcription
- Percussion and pitch-based instrument support

⚡ **Production Ready**
- RESTful API with comprehensive documentation
- Health checks and monitoring
- GPU acceleration support

---

## Quick Start

### Prerequisites

- Python 3.9+
- 8GB+ RAM (16GB recommended)
- 10GB disk space
- (Optional) NVIDIA GPU with CUDA

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/music-to-midi-api.git
cd music-to-midi-api

# 2. Download YourMT3 checkpoint (~536MB)
./setup_checkpoint.sh

# 3. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Start server
python -m app.main
```

Server available at: **http://localhost:8000**

API Documentation: **http://localhost:8000/docs**

---

## Usage

### Upload Audio

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@song.mp3"
```

Response:
```json
{
  "job_id": "abc-123-def-456",
  "message": "File uploaded successfully",
  "filename": "song.mp3",
  "file_size": 5242880,
  "created_at": "2025-10-09T10:30:00"
}
```

### Start Processing

```bash
curl -X POST http://localhost:8000/api/v1/predict/abc-123-def-456
```

### Check Status

```bash
curl http://localhost:8000/api/v1/status/abc-123-def-456
```

Response:
```json
{
  "job_id": "abc-123-def-456",
  "status": "processing",
  "progress": 45,
  "message": "Transcribing drums stem to MIDI..."
}
```

### Get Results

```bash
curl http://localhost:8000/api/v1/results/abc-123-def-456
```

Response:
```json
{
  "job_id": "abc-123-def-456",
  "song_info": {
    "filename": "song.mp3",
    "duration": 180.5,
    "tempo": 120,
    "total_beats": 450
  },
  "stems": {
    "bass": {
      "type": "midi",
      "stem": "bass",
      "midi_path": "/uploads/abc-123-def-456/midi/abc-123-def-456_bass.mid",
      "midi_url": "/api/v1/files/abc-123-def-456_bass.mid",
      "program_range": [33, 40],
      "status": "processed"
    },
    "drums": {
      "type": "midi",
      "stem": "drums",
      "midi_path": "/uploads/abc-123-def-456/midi/abc-123-def-456_drums.mid",
      "midi_url": "/api/v1/files/abc-123-def-456_drums.mid",
      "status": "processed"
    },
    "other": {
      "type": "midi",
      "stem": "other",
      "midi_path": "/uploads/abc-123-def-456/midi/abc-123-def-456_other.mid",
      "midi_url": "/api/v1/files/abc-123-def-456_other.mid",
      "status": "processed"
    },
    "vocals": {
      "type": "midi",
      "stem": "vocals",
      "midi_path": "/uploads/abc-123-def-456/midi/abc-123-def-456_vocals.mid",
      "midi_url": "/api/v1/files/abc-123-def-456_vocals.mid",
      "status": "processed"
    }
  },
  "processing_summary": {
    "stems_processed": 4,
    "total_midi_files": 4,
    "model": "YourMT3 (YPTF.MoE+Multi, 536M params)",
    "separator": "Demucs htdemucs (4-stem)"
  }
}
```

### Download MIDI

```bash
curl -O http://localhost:8000/api/v1/files/abc-123-def-456_bass.mid
```

---

## Architecture

### Processing Pipeline

```
Audio Input
    ↓
[Demucs Stem Separation]
    ↓
├─ Bass  → [YourMT3] → bass.mid    (GM Programs 32-39)
├─ Drums → [YourMT3] → drums.mid   (Percussion track)
├─ Other → [YourMT3] → other.mid   (Melodic instruments)
└─ Vocals → [VAD]    → vocals.mid   (Voice activity only)
    ↓
MIDI Files Output
```

### Tech Stack

**Backend**:
- FastAPI (async Python web framework)
- PyTorch 2.1+ (deep learning)
- Uvicorn (ASGI server)

**AI Models**:
- YourMT3 (YPTF.MoE+Multi, 536M parameters)
- Demucs htdemucs (4-stem separator)

**Audio Processing**:
- librosa (audio analysis)
- torchaudio (PyTorch audio)
- soundfile (audio I/O)

---

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root endpoint, service info |
| GET | `/health` | Health check, model status |
| GET | `/model/info` | Model information |
| POST | `/api/v1/upload` | Upload audio file |
| POST | `/api/v1/predict/{job_id}` | Start transcription |
| GET | `/api/v1/status/{job_id}` | Check processing status |
| GET | `/api/v1/results/{job_id}` | Get transcription results |
| GET | `/api/v1/files/{filename}` | Download MIDI file |
| DELETE | `/api/v1/jobs/{job_id}` | Clean up job files and data |

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Configuration

### Environment Variables

Create `.env` file:

```bash
# Server
PORT=8000
HOST=0.0.0.0

# Model
SKIP_MODEL_LOADING=0  # Set to 1 to skip model loading (testing mode)

# Security
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Performance
MAX_UPLOAD_SIZE=100  # MB
REQUEST_TIMEOUT=600  # seconds
```

### GPU Support

Automatically detected. Verify with:

```python
import torch
print(torch.cuda.is_available())  # Should print True if GPU available
```

---

## Performance

### Processing Times (CPU)

| Duration | Stem Separation | MIDI Transcription | Total |
|----------|----------------|-------------------|-------|
| 1 minute | ~30-60s | ~2-3 minutes | ~3-5 min |
| 3 minutes | ~90-180s | ~6-9 minutes | ~10-15 min |

### GPU Acceleration

**5-10x faster** with NVIDIA GPU (CUDA):

| Duration | Total Time (GPU) |
|----------|-----------------|
| 1 minute | ~30-60s |
| 3 minutes | ~2-3 minutes |

### Resource Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8GB | 16GB |
| CPU | 4 cores | 8 cores |
| GPU | - | NVIDIA with 4GB+ VRAM |
| Disk | 10GB | 20GB+ |

---

## Development

### Project Structure

```
music-to-midi-api/
├── app/
│   ├── api/
│   │   ├── routes.py          # API endpoints
│   │   └── models.py          # Pydantic models
│   ├── services/
│   │   ├── yourmt3_service.py # YourMT3 integration
│   │   ├── demucs_separator.py # Stem separation
│   │   ├── stem_processors.py # Per-stem processing
│   │   └── transcription.py   # Pipeline orchestration
│   └── main.py                # FastAPI app
├── amt/                       # YourMT3 checkpoint (not in git)
├── uploads/                   # User uploads (not in git)
├── logs/                      # Application logs
├── tests/                     # Test suite
├── requirements.txt           # Python dependencies
└── setup_checkpoint.sh        # Checkpoint download script
```

### Running Tests

```bash
# Verification test
python test_local_amt.py

# Sanity test
python sanity_test.py

# Full test suite
pytest tests/ -v
```

### Development Mode

```bash
# Auto-reload on file changes
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Test without model loading
SKIP_MODEL_LOADING=1 python -m app.main
```

---

## Deployment

### Manual Deployment to Server Instance

Complete guide for deploying to a server instance (Infomaniak, DigitalOcean, etc.)

#### Prerequisites

**Recommended Server Specs**:
- OS: Ubuntu 22.04 LTS
- RAM: 16GB minimum (8GB works but slower)
- CPU: 4+ cores
- Disk: 20GB free space
- Python 3.9+

**Firewall Rules**:
- **Inbound**: Port 22 (SSH, your IP only), Port 8000 (API, 0.0.0.0/0)
- **Outbound**: All traffic allowed

#### Step 1: Initial Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3.10 python3.10-venv python3-pip git

# Install system dependencies
sudo apt install -y ffmpeg libsndfile1
```

#### Step 2: Clone Repository

```bash
# Clone from GitHub
cd ~
git clone https://github.com/Pyzeur-ColonyLab/music-to-midi-api.git
cd music-to-midi-api
```

#### Step 3: Transfer YourMT3 Checkpoint

**Option A: From Local Machine (Recommended)**

On your local machine:
```bash
# Transfer checkpoint directory to instance
scp -r amt/ ubuntu@YOUR_INSTANCE_IP:/home/ubuntu/music-to-midi-api/

# Example:
scp -r amt/ ubuntu@83.228.227.26:/home/ubuntu/music-to-midi-api/
```

**Option B: Download from Hugging Face**

On the instance:
```bash
./setup_checkpoint.sh
# Select option 1: "Download from Hugging Face"
```

See [TRANSFER_GUIDE.md](TRANSFER_GUIDE.md) for detailed transfer instructions.

#### Step 4: Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 5: Configure Environment

```bash
# Create .env file (optional)
cat > .env << EOF
PORT=8000
HOST=0.0.0.0
MAX_UPLOAD_SIZE_MB=500
EOF
```

#### Step 6: Start Server

**Development Mode** (auto-reload):
```bash
python3 -m app.main
```

**Production Mode** (recommended):
```bash
# Install screen for background process
sudo apt install -y screen

# Start server in screen session
screen -S music-api
python3 -m app.main

# Detach from screen: Ctrl+A then D
# Reattach: screen -r music-api
```

**Production with systemd** (best for production):

Create service file:
```bash
sudo tee /etc/systemd/system/music-to-midi.service > /dev/null << EOF
[Unit]
Description=Music-to-MIDI API Service
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
EOF

# Enable and start service
sudo systemctl enable music-to-midi
sudo systemctl start music-to-midi

# Check status
sudo systemctl status music-to-midi

# View logs
sudo journalctl -u music-to-midi -f
```

#### Step 7: Verify Deployment

```bash
# Check health
curl http://localhost:8000/health

# Should return:
# {"status":"healthy","model_loaded":true,"device":"cpu","gpu_available":false}
```

#### Step 8: Test Complete Pipeline

```bash
# Upload test file
curl -X POST http://YOUR_INSTANCE_IP:8000/api/v1/upload \
  -F "file=@test.mp3"

# Note the job_id from response

# Start transcription
curl -X POST http://YOUR_INSTANCE_IP:8000/api/v1/predict/JOB_ID

# Check status
curl http://YOUR_INSTANCE_IP:8000/api/v1/status/JOB_ID

# Get results when completed
curl http://YOUR_INSTANCE_IP:8000/api/v1/results/JOB_ID
```

#### Management Commands

```bash
# Stop server
sudo systemctl stop music-to-midi

# Restart server
sudo systemctl restart music-to-midi

# View logs
sudo journalctl -u music-to-midi -f

# Update code
cd ~/music-to-midi-api
git pull origin main
sudo systemctl restart music-to-midi
```

### Advanced Configuration

For advanced production configurations, see [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Nginx reverse proxy configuration
- SSL/TLS certificates (Let's Encrypt)
- Monitoring and alerting
- Performance optimization

---

## Troubleshooting

### Model Won't Load

```bash
# Verify checkpoint exists
ls -lh amt/logs/2024/.../checkpoints/last.ckpt

# Run verification
python test_local_amt.py

# Check dependencies
pip install -r requirements.txt
```

### Out of Memory

```bash
# Reduce concurrent processing
# Single worker mode (default)

# Monitor memory
watch -n 1 free -h
```

### Slow Processing

```bash
# Check GPU availability
python -c "import torch; print(torch.cuda.is_available())"

# Use GPU if available (automatic)
# Or reduce audio file length
```

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

### Model Licenses

- **YourMT3**: Apache 2.0 License
- **Demucs**: MIT License

---

## Acknowledgments

- [YourMT3](https://github.com/mimbres/YourMT3) - Advanced audio-to-MIDI transcription
- [Demucs](https://github.com/facebookresearch/demucs) - Music source separation
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework

---

## Support

- **Documentation**: http://localhost:8000/docs
- **Issues**: GitHub Issues

---

## Changelog

### v1.0.0 (2025-10-09)

- ✨ Initial release
- 🎵 YourMT3 integration for MIDI transcription
- 🎚️ Demucs 4-stem separation
- 📡 RESTful API with comprehensive endpoints
- 📖 Complete documentation

---

**Assisted by Claude Code**
