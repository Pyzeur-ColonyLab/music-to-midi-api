"""
Services layer for Music-to-MIDI API
Business logic and orchestration
"""

# YourMT3 integration
from .yourmt3_service import (
    load_yourmt3,
    get_yourmt3_model,
    transcribe_audio_to_midi,
    get_model_info,
    unload_model
)

# Demucs stem separation
from .demucs_separator import (
    load_demucs_model,
    get_demucs_model,
    separate_stems
)

# Transcription pipeline
from .transcription import transcribe_audio

# Stem processors
from .stem_processors import (
    StemProcessor,
    BassStemProcessor,
    DrumsStemProcessor,
    OtherStemProcessor,
    VocalsStemProcessor,
    create_stem_processor
)

__all__ = [
    # YourMT3 model management
    'load_yourmt3',
    'get_yourmt3_model',
    'transcribe_audio_to_midi',
    'get_model_info',
    'unload_model',
    # Demucs stem separation
    'load_demucs_model',
    'get_demucs_model',
    'separate_stems',
    # Transcription
    'transcribe_audio',
    # Stem processors
    'StemProcessor',
    'BassStemProcessor',
    'DrumsStemProcessor',
    'OtherStemProcessor',
    'VocalsStemProcessor',
    'create_stem_processor',
]
