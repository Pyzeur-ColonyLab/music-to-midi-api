"""
Transcription Service
Core audio-to-MIDI transcription logic
"""

import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from app.services.model_loader import get_model_instance

logger = logging.getLogger(__name__)


def transcribe_audio(
    audio_path: str,
    confidence_threshold: float = 0.1,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Transcribe audio file to MIDI using stem-based processing

    This is the main transcription function that uses the 3-stem specialized models:
    1. Load and analyze audio file
    2. Detect beats and tempo
    3. Separate into stems (bass, drums, other, vocals)
    4. Process each stem with specialized model
    5. Generate comprehensive analysis results

    Args:
        audio_path: Path to audio file (mp3, wav, flac, m4a)
        confidence_threshold: Minimum confidence for predictions (0.0-1.0)
        progress_callback: Optional callback function(progress: int, message: str)
                          Called with progress percentage and status message

    Returns:
        Dictionary containing:
            - song_info: Duration, tempo, beats, etc.
            - timeline: Beat-by-beat instrument predictions
            - processing_summary: Stats about processing
            - stems: Individual stem analysis results

    Raises:
        FileNotFoundError: If audio file not found
        RuntimeError: If transcription fails
        ValueError: If model not loaded

    Example:
        >>> result = transcribe_audio("song.mp3", confidence_threshold=0.2)
        >>> print(f"Duration: {result['song_info']['duration']:.1f}s")
        >>> print(f"Tempo: {result['song_info']['tempo']} BPM")
    """
    # Validate audio file exists
    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Get model instance
    model = get_model_instance()
    if model is None:
        raise ValueError("Model not loaded. Initialize model on startup.")

    logger.info(f"Starting transcription: {audio_path}")

    if progress_callback:
        progress_callback(0, "Starting audio analysis...")

    try:
        # Run full analysis using stem-integrated classifier
        result = model.analyze_file(
            file_path=str(audio_file),
            confidence_threshold=confidence_threshold,
            progress_callback=progress_callback
        )

        logger.info(f"Transcription completed successfully")
        if progress_callback:
            progress_callback(100, "Transcription completed")

        return result

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        if progress_callback:
            progress_callback(-1, f"Transcription failed: {str(e)}")
        raise RuntimeError(f"Transcription failed: {e}")


def transcribe_with_stems(
    audio_path: str,
    stems_to_process: Optional[list] = None,
    confidence_threshold: float = 0.1,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Transcribe audio with explicit stem selection

    Allows selecting specific stems for processing (useful for testing or optimization)

    Args:
        audio_path: Path to audio file
        stems_to_process: List of stems to process ['bass', 'drums', 'other', 'vocals']
                         None = process all stems
        confidence_threshold: Minimum confidence for predictions
        progress_callback: Optional progress callback

    Returns:
        Analysis results dictionary (same format as transcribe_audio)

    Example:
        >>> # Only process bass and drums
        >>> result = transcribe_with_stems("song.mp3", stems_to_process=['bass', 'drums'])
    """
    if stems_to_process is None:
        stems_to_process = ['bass', 'drums', 'other', 'vocals']

    logger.info(f"Transcribing with stems: {stems_to_process}")

    # For now, this delegates to main transcribe_audio
    # In future, could optimize to only process selected stems
    result = transcribe_audio(
        audio_path=audio_path,
        confidence_threshold=confidence_threshold,
        progress_callback=progress_callback
    )

    # Filter results to only requested stems
    if 'stems' in result:
        result['stems'] = {
            stem: data for stem, data in result['stems'].items()
            if stem in stems_to_process
        }

    return result


def get_transcription_stats(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract summary statistics from transcription result

    Args:
        result: Transcription result dictionary

    Returns:
        Dictionary with summary stats:
            - total_duration: Audio duration in seconds
            - total_beats: Number of beats detected
            - tempo: Tempo in BPM
            - stems_processed: Number of stems processed
            - total_segments: Total audio segments analyzed
            - instruments_detected: Number of unique instruments
    """
    song_info = result.get('song_info', {})
    processing_summary = result.get('processing_summary', {})

    stats = {
        'total_duration': song_info.get('duration', 0),
        'total_beats': len(song_info.get('beats', [])),
        'tempo': song_info.get('tempo', 0),
        'stems_processed': processing_summary.get('stems_processed', 0),
        'total_segments': processing_summary.get('total_segments', 0),
        'instruments_detected': len(processing_summary.get('unique_instruments', []))
    }

    return stats
