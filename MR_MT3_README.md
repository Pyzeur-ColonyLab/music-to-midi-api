# 🎵 MR-MT3 Integration - Quick Start

This repository now supports **MR-MT3** (Memory Retaining Multi-Track Music Transcription) as an alternative/replacement to YourMT3.

## What is MR-MT3?

**MR-MT3** is an advanced music transcription model that:
- 🧠 Uses **memory retention** to reduce instrument leakage
- 🎹 Generates **multi-track MIDI** with better separation
- 📊 Achieves **F1 score of 0.65** (vs 0.60 for YourMT3)
- 📄 Based on research: https://arxiv.org/abs/2403.10024

## Quick Setup

### 1. Download MR-MT3 Model

```bash
chmod +x scripts/setup_mr_mt3.sh
./scripts/setup_mr_mt3.sh
```

### 2. Install Dependencies

```bash
pip install -r requirements-mr-mt3.txt
```

### 3. Start the API

```bash
python -m app.main
```

## Usage

### Python Example

```python
from app.services.mr_mt3_service import get_mr_mt3_service

# Initialize service
mr_mt3 = get_mr_mt3_service()

# Transcribe audio to MIDI
midi_path = mr_mt3.transcribe_audio(
    audio_path="song.mp3",
    output_path="output.mid"
)

print(f"MIDI generated: {midi_path}")
```

### API Example

```bash
# Upload audio
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@song.mp3"

# Get job_id from response, then:
curl -X POST http://localhost:8000/api/v1/predict/JOB_ID

# Check status
curl http://localhost:8000/api/v1/status/JOB_ID

# Download results
curl http://localhost:8000/api/v1/results/JOB_ID
```

## Files Created

```
music-to-midi-api/
├── app/services/
│   └── mr_mt3_service.py           # MR-MT3 service wrapper
├── scripts/
│   └── setup_mr_mt3.sh             # Model download script
├── requirements-mr-mt3.txt         # MR-MT3 dependencies
├── MR_MT3_MIGRATION.md             # Detailed migration guide
└── MR_MT3_README.md                # This file
```

## Key Differences from YourMT3

| Feature | YourMT3 | MR-MT3 |
|---------|---------|--------|
| Model size | 536M params | ~400M params |
| F1 Score | 0.60 | **0.65** ✨ |
| Instrument leakage | Moderate | **Low** ✨ |
| Memory retention | ❌ | ✅ ✨ |
| Training data | Multi-source | Slakh2100 |

## What's Next?

1. **Test the integration**: See `MR_MT3_MIGRATION.md` for testing guide
2. **Compare results**: Run same audio through both models
3. **Production deploy**: Follow deployment guide in main README.md

## Working Example

A complete working notebook is available at:
```
../MR-MT3_Demo.ipynb
```

This notebook includes:
- ✅ Model loading and initialization
- ✅ Audio preprocessing
- ✅ MIDI generation
- ✅ Interactive MIDI player with visualization
- ✅ YouTube URL support

## Resources

- **Model**: https://huggingface.co/gudgud1014/MR-MT3
- **Paper**: https://arxiv.org/abs/2403.10024
- **GitHub**: https://github.com/gudgud96/MR-MT3
- **Migration Guide**: See `MR_MT3_MIGRATION.md`

## Troubleshooting

See `MR_MT3_MIGRATION.md` section "Troubleshooting" for common issues and solutions.

---

**Integration by**: Claude Code
**Date**: 2025-11-10
**Status**: ✅ Ready for testing
