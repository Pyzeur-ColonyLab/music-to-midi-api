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
- Docker support for easy deployment
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

### Docker

```bash
# Download checkpoint first
./setup_checkpoint.sh

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
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
  "stems": {
    "bass": {
      "midi_path": "/path/to/abc-123-def-456_bass.mid",
      "midi_url": "/api/v1/files/abc-123-def-456_bass.mid",
      "program_range": [33, 40],
      "status": "processed"
    },
    "drums": { ... },
    "other": { ... },
    "vocals": { ... }
  },
  "processing_summary": {
    "stems_processed": 4,
    "total_midi_files": 4,
    "model": "YourMT3 (YPTF.MoE+Multi, 536M params)"
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
├── Dockerfile                 # Docker image
├── docker-compose.yml         # Docker Compose config
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

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide including:

- Production server setup (Gunicorn)
- Nginx reverse proxy
- SSL/TLS configuration
- Cloud deployment (AWS, GCP, Azure, DigitalOcean)
- Docker/Kubernetes
- Monitoring and scaling

Quick Docker deployment:

```bash
# Build
docker build -t music-to-midi-api .

# Run
docker run -d \
  -p 8000:8000 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/amt:/app/amt \
  --name music-to-midi-api \
  music-to-midi-api
```

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
- 🐳 Docker support
- 📖 Complete documentation

---

**Assisted by Claude Code**
