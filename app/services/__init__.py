"""
Services layer for Music-to-MIDI API
Business logic and orchestration
"""

from .model_loader import load_yourmt3_model, get_model_instance, get_model_info
from .transcription import transcribe_audio, transcribe_with_stems, get_transcription_stats
from .midi_processor import analyze_midi, midi_to_json, apply_stem_constraints
from .stem_separator import separate_stems, cleanup_stems, get_available_models
from .stem_processors import (
    StemProcessor,
    BassStemProcessor,
    DrumsStemProcessor,
    OtherStemProcessor,
    VocalsStemProcessor,
    create_stem_processor
)
from .vad import detect_voice_activity, get_vad_statistics, filter_short_segments

__all__ = [
    # Model management
    'load_yourmt3_model',
    'get_model_instance',
    'get_model_info',
    # Transcription
    'transcribe_audio',
    'transcribe_with_stems',
    'get_transcription_stats',
    # MIDI processing
    'analyze_midi',
    'midi_to_json',
    'apply_stem_constraints',
    # Stem separation
    'separate_stems',
    'cleanup_stems',
    'get_available_models',
    # Stem processors
    'StemProcessor',
    'BassStemProcessor',
    'DrumsStemProcessor',
    'OtherStemProcessor',
    'VocalsStemProcessor',
    'create_stem_processor',
    # Voice Activity Detection
    'detect_voice_activity',
    'get_vad_statistics',
    'filter_short_segments'
]
