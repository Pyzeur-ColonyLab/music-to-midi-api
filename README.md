# Music-to-MIDI API Service

Production API service for audio-to-MIDI transcription using YourMT3 with stem-based processing.

## Overview

Convert audio files (mp3, wav, flac, m4a) to MIDI files with optional stem-based processing for improved accuracy.

### Features

- **Direct transcription**: Single-pass YourMT3 transcription (~30s for 3min audio)
- **Stem-based transcription**: Demucs separation → per-stem processing (~90s for 3min audio)
  - Bass stem: YourMT3 MIDI transcription
  - Other stem: YourMT3 MIDI transcription
  - Drums stem: YourMT3 MIDI transcription
  - Vocals stem: Voice activity detection (VAD)
- **3-Stem Specialized Models**: 24 instrument classes across bass, drums, other stems
  - Bass: 99% accuracy (8 classes)
  - Drums: 98% accuracy (8 classes)
  - Other: 84% accuracy (8 classes)

## Architecture

### Technology Stack

- **Framework**: FastAPI (async, auto-documented, Pydantic validation)
- **Model**: YourMT3 - YPTF.MoE+Multi (noPS) 536M parameters
- **Stem Separation**: Demucs htdemucs (4-stem)
- **MIDI Processing**: pretty_midi
- **Deployment**: Docker with NVIDIA CUDA base (GPU/CPU compatible)

### Project Structure

```
music-to-midi-api/
├── app/
│   ├── main.py                     # FastAPI application
│   ├── api/                        # API endpoints
│   ├── services/                   # Business logic
│   ├── models/                     # ML models
│   │   ├── stem_specific_classifier.py
│   │   ├── stem_integrated_classifier.py
│   │   └── 3_stems_models/         # Pre-trained models
│   ├── core/                       # Configuration
│   └── utils/                      # Utilities
├── tests/                          # Test suite
├── deploy/                         # Deployment scripts
├── scripts/                        # Utility scripts
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Installation

### Prerequisites

- Python 3.10+
- ffmpeg (for audio processing)
- CUDA (optional, for GPU acceleration)

### Setup

```bash
# Clone repository
git clone https://github.com/Pyzeur-ColonyLab/music-to-midi-api.git
cd music-to-midi-api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download pre-trained models (if not included)
python scripts/download_models.py
```

## Usage

### Start API Server

```bash
# Development mode
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### API Endpoints

#### Health Check
```bash
GET /
```

#### Model Information
```bash
GET /model/info
```

#### Upload Audio File
```bash
POST /upload
Content-Type: multipart/form-data

{
  "file": <audio_file>
}

Response:
{
  "job_id": "abc123",
  "message": "File uploaded successfully"
}
```

#### Start Transcription
```bash
POST /predict/{job_id}
Content-Type: application/json

{
  "confidence_threshold": 0.1
}

Response:
{
  "job_id": "abc123",
  "message": "Analysis completed successfully",
  "duration": 180.5,
  "tempo": 120,
  "total_beats": 450,
  "stems_processed": 3,
  "total_segments": 45
}
```

#### Get Job Status
```bash
GET /status/{job_id}

Response:
{
  "job_id": "abc123",
  "status": "completed",
  "progress": 100,
  "message": "Analysis completed"
}
```

#### Get Results
```bash
GET /results/{job_id}

Response:
{
  "job_id": "abc123",
  "filename": "song.mp3",
  "analysis_result": {
    "song_info": {...},
    "timeline": {...},
    "processing_summary": {...}
  }
}
```

## GM MIDI Classification

Instrument classification follows General MIDI specification with stem-based constraints:

### Stem Mapping

- **Bass Stem**: Programs 33-40 (GM Bass family only)
- **Others Stem**: Programs 1-32, 41-112, 121-128 (melodic/harmonic instruments)
- **Drums Stem**: Programs 113-120 + Channel 10 GM percussion
- **Vocals Stem**: VAD only (v1.0), future speech-to-text

### Constraint Logic

```python
# If MT3 predicts non-bass program on bass stem, correct to program 33
if stem_type == 'bass':
    if midi_track.program not in range(32, 40):
        midi_track.program = 33  # Electric Bass (finger)
```

See [MT3/SESSION_2025-10-07_GM_Classification.md](../MT3/SESSION_2025-10-07_GM_Classification.md) for details.

## Deployment

### systemd Service (Recommended)

```bash
# Run setup script
./deploy/setup.sh

# Service management
sudo systemctl status music-to-midi-api
sudo systemctl restart music-to-midi-api
sudo journalctl -u music-to-midi-api -f
```

### Docker (Alternative)

```bash
# Build image
docker build -t music-to-midi-api .

# Run container
docker run -p 8000:8000 -v $(pwd)/uploads:/app/uploads music-to-midi-api
```

## Performance

### Processing Time (3-minute audio)

| Mode   | Hardware      | Target Time | Max Acceptable |
|--------|---------------|-------------|----------------|
| Direct | GPU (A10G)    | 30s         | 60s            |
| Direct | CPU (8 cores) | 5min        | 8min           |
| Stems  | GPU (A10G)    | 90s         | 120s           |
| Stems  | CPU (8 cores) | 12min       | 15min          |

### Resource Usage

| Component          | GPU Memory | CPU Memory | Disk Space |
|--------------------|------------|------------|------------|
| YourMT3 Model      | 8GB        | -          | 600MB      |
| Demucs Model       | 2GB        | -          | 80MB       |
| Audio Processing   | 1GB        | 2GB        | 100MB/file |
| **Total**          | ~11GB      | ~4GB       | ~1GB       |

## Development

### Run Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_transcription.py

# With coverage
pytest --cov=app tests/
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint
flake8 app/ tests/
```

## Documentation

- [API Specification](../MT3/API_SPECIFICATION.md) - Complete technical specification
- [GM Classification Session](../MT3/SESSION_2025-10-07_GM_Classification.md) - MIDI classification decisions
- [MIDI Reference](../MT3/MIDI%20Ref%20-%20Feuille%201.csv) - GM program mappings

## License

[Your License]

## Contributing

[Your Contributing Guidelines]

## Support

[Your Support Information]
