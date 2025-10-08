"""
Voice Activity Detection (VAD) Service
Detects speech/vocal activity in audio files
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)


def detect_voice_activity(
    audio_path: str,
    frame_duration_ms: int = 30,
    aggressiveness: int = 2
) -> List[Dict[str, Any]]:
    """
    Detect voice activity in audio file using WebRTC VAD

    Args:
        audio_path: Path to audio file (must be 16kHz mono for VAD)
        frame_duration_ms: Frame size in milliseconds (10, 20, or 30)
        aggressiveness: VAD aggressiveness level (0-3, higher = more aggressive filtering)
                       0 = least aggressive, 3 = most aggressive

    Returns:
        List of voice activity segments:
        [
            {'start': 0.0, 'end': 5.2, 'active': True},
            {'start': 5.2, 'end': 8.1, 'active': False},
            ...
        ]

    Raises:
        FileNotFoundError: If audio file not found
        RuntimeError: If VAD processing fails

    Example:
        >>> segments = detect_voice_activity("vocals.wav")
        >>> active_time = sum(s['end'] - s['start'] for s in segments if s['active'])
        >>> print(f"Voice active for {active_time:.1f}s")
    """
    try:
        import webrtcvad
        import librosa
        import soundfile as sf

        # Validate input file
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Running VAD on: {audio_file.name}")
        logger.info(f"Aggressiveness: {aggressiveness}, Frame: {frame_duration_ms}ms")

        # Initialize VAD
        vad = webrtcvad.Vad(aggressiveness)

        # Load and convert audio to 16kHz mono (required for WebRTC VAD)
        audio, original_sr = librosa.load(str(audio_file), sr=None, mono=True)

        # Resample to 16kHz if needed
        if original_sr != 16000:
            audio = librosa.resample(audio, orig_sr=original_sr, target_sr=16000)

        sample_rate = 16000

        # Convert to int16 format (required for VAD)
        audio_int16 = (audio * 32767).astype(np.int16)

        # Process in frames
        frame_samples = int(sample_rate * frame_duration_ms / 1000)
        segments = []

        for i in range(0, len(audio_int16), frame_samples):
            frame = audio_int16[i:i + frame_samples]

            # Pad last frame if needed
            if len(frame) < frame_samples:
                frame = np.pad(frame, (0, frame_samples - len(frame)))

            # Convert to bytes
            frame_bytes = frame.tobytes()

            # VAD decision
            try:
                is_speech = vad.is_speech(frame_bytes, sample_rate)
            except Exception:
                # Frame might be too short or invalid, skip
                is_speech = False

            time_start = i / sample_rate
            time_end = (i + frame_samples) / sample_rate

            # Merge consecutive active segments
            if segments and segments[-1]['active'] == is_speech:
                segments[-1]['end'] = time_end
            else:
                segments.append({
                    'start': time_start,
                    'end': time_end,
                    'active': is_speech
                })

        logger.info(f"VAD completed: {len(segments)} segments detected")
        return segments

    except ImportError as e:
        logger.error(f"VAD dependencies not installed: {e}")
        raise RuntimeError(
            "VAD dependencies not available. "
            "Install with: pip install webrtcvad librosa soundfile"
        )
    except Exception as e:
        logger.error(f"VAD processing failed: {e}")
        raise RuntimeError(f"VAD processing failed: {e}")


def get_vad_statistics(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate statistics from VAD segments

    Args:
        segments: List of VAD segments from detect_voice_activity()

    Returns:
        {
            'total_duration': float,  # Total audio duration in seconds
            'voice_active_duration': float,  # Voice active time in seconds
            'voice_inactive_duration': float,  # Silence duration in seconds
            'voice_percentage': float,  # Percentage of voice activity (0-100)
            'num_segments': int,  # Total number of segments
            'num_voice_segments': int  # Number of voice-active segments
        }

    Example:
        >>> segments = detect_voice_activity("vocals.wav")
        >>> stats = get_vad_statistics(segments)
        >>> print(f"Voice activity: {stats['voice_percentage']:.1f}%")
    """
    if not segments:
        return {
            'total_duration': 0.0,
            'voice_active_duration': 0.0,
            'voice_inactive_duration': 0.0,
            'voice_percentage': 0.0,
            'num_segments': 0,
            'num_voice_segments': 0
        }

    total_duration = segments[-1]['end']
    voice_active = sum(
        seg['end'] - seg['start']
        for seg in segments
        if seg['active']
    )
    voice_inactive = total_duration - voice_active

    return {
        'total_duration': total_duration,
        'voice_active_duration': voice_active,
        'voice_inactive_duration': voice_inactive,
        'voice_percentage': (voice_active / total_duration * 100) if total_duration > 0 else 0.0,
        'num_segments': len(segments),
        'num_voice_segments': sum(1 for seg in segments if seg['active'])
    }


def filter_short_segments(
    segments: List[Dict[str, Any]],
    min_duration: float = 0.3
) -> List[Dict[str, Any]]:
    """
    Filter out very short voice segments (likely noise)

    Args:
        segments: List of VAD segments
        min_duration: Minimum segment duration in seconds

    Returns:
        Filtered segments with short ones removed/merged

    Example:
        >>> segments = detect_voice_activity("vocals.wav")
        >>> filtered = filter_short_segments(segments, min_duration=0.5)
    """
    filtered = []

    for seg in segments:
        duration = seg['end'] - seg['start']

        if duration >= min_duration:
            filtered.append(seg)
        elif filtered and not seg['active']:
            # Extend previous silence segment
            filtered[-1]['end'] = seg['end']
        else:
            # Short active segment - convert to inactive
            filtered.append({
                'start': seg['start'],
                'end': seg['end'],
                'active': False
            })

    return filtered


def export_vad_to_json(
    segments: List[Dict[str, Any]],
    output_path: str,
    include_stats: bool = True
):
    """
    Export VAD results to JSON file

    Args:
        segments: VAD segments
        output_path: Path to output JSON file
        include_stats: Whether to include statistics

    Example:
        >>> segments = detect_voice_activity("vocals.wav")
        >>> export_vad_to_json(segments, "vad_results.json")
    """
    import json

    output = {
        'segments': segments
    }

    if include_stats:
        output['statistics'] = get_vad_statistics(segments)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

    logger.info(f"VAD results exported to: {output_path}")
