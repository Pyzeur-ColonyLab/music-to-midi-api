"""
Transcription Service
Core audio-to-MIDI transcription logic using YourMT3
"""

import logging
import os
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from app.services.yourmt3_service import get_yourmt3_model
from app.services.stem_processors import create_stem_processor
from app.services.demucs_separator import separate_stems

logger = logging.getLogger(__name__)


def transcribe_audio(
    audio_path: str,
    job_id: str,
    confidence_threshold: float = 0.1,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Transcribe audio file to MIDI using YourMT3 with stem-based processing

    Pipeline:
    1. Load and analyze audio file
    2. Separate into stems (bass, drums, other, vocals) using Demucs
    3. Process each stem with YourMT3 to generate MIDI
    4. Return comprehensive analysis results with MIDI URLs

    Args:
        audio_path: Path to audio file (mp3, wav, flac, m4a)
        job_id: Unique job identifier for organizing outputs
        confidence_threshold: Minimum confidence for predictions (0.0-1.0)
        progress_callback: Optional callback function(progress: int, message: str)
                          Called with progress percentage and status message

    Returns:
        Dictionary containing:
            - song_info: Duration, tempo, beats, etc.
            - stems: Individual stem MIDI results with download URLs
            - processing_summary: Stats about processing

    Raises:
        FileNotFoundError: If audio file not found
        RuntimeError: If transcription fails
        ValueError: If model not loaded

    Example:
        >>> result = transcribe_audio("song.mp3", job_id="abc-123")
        >>> print(f"Bass MIDI: {result['stems']['bass']['midi_url']}")
    """
    # Validate audio file exists
    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Get YourMT3 model instance
    model = get_yourmt3_model()
    if model is None:
        raise ValueError("YourMT3 model not loaded. Initialize model on startup.")

    logger.info(f"Starting transcription: {audio_path} (Job: {job_id})")

    if progress_callback:
        progress_callback(0, "Starting audio analysis...")

    try:
        # Step 1: Separate stems using Demucs (10% progress)
        if progress_callback:
            progress_callback(5, "Separating audio stems...")

        stems_dir = f"uploads/{job_id}/stems"
        os.makedirs(stems_dir, exist_ok=True)

        stem_paths = separate_stems(
            audio_path=audio_path,
            output_dir=stems_dir,
            model_name="htdemucs"  # 4-stem Demucs
        )

        # Create symlinks/copies with job_id prefix for frontend compatibility
        # Frontend expects: {job_id}_bass.wav, {job_id}_drums.wav, etc.
        import shutil
        for stem_name, stem_path in list(stem_paths.items()):
            prefixed_filename = f"{job_id}_{stem_name}.wav"
            prefixed_path = os.path.join(stems_dir, prefixed_filename)

            try:
                # Create symlink (preferred on Unix systems)
                if os.name != 'nt':  # Unix/Linux/Mac
                    if not os.path.exists(prefixed_path):
                        os.symlink(os.path.basename(stem_path), prefixed_path)
                else:  # Windows - use copy
                    if not os.path.exists(prefixed_path):
                        shutil.copy2(stem_path, prefixed_path)

                logger.info(f"   Created frontend-compatible path: {prefixed_filename}")
            except Exception as e:
                logger.warning(f"Could not create prefixed stem file: {e}")

        if progress_callback:
            progress_callback(20, "Stems separated successfully")

        # Step 2: Process each stem with YourMT3 (20% → 90%)
        stems_result = {}
        progress_per_stem = 70 / len(stem_paths)  # 70% total for stem processing
        current_progress = 20
        failed_stems = []

        for stem_name, stem_path in stem_paths.items():
            if progress_callback:
                progress_callback(
                    int(current_progress),
                    f"Transcribing {stem_name} stem to MIDI..."
                )

            try:
                # Create appropriate processor for this stem
                processor = create_stem_processor(stem_name, model=model)

                # Process stem to generate MIDI
                stem_result = processor.process(
                    audio_path=stem_path,
                    job_id=job_id,
                    output_dir=f"uploads/{job_id}/midi"
                )

                stems_result[stem_name] = stem_result
                current_progress += progress_per_stem

                logger.info(
                    f"✅ Processed {stem_name} stem successfully: {stem_result.get('midi_path', 'N/A')}"
                )

            except Exception as e:
                logger.error(f"❌ Failed to process {stem_name} stem: {e}")
                logger.exception(f"Full error for {stem_name} stem:")

                # Store error info but continue processing other stems
                stems_result[stem_name] = {
                    'status': 'failed',
                    'stem': stem_name,
                    'error': str(e),
                    'midi_path': None
                }
                failed_stems.append(stem_name)
                current_progress += progress_per_stem

        # Log summary of failures
        if failed_stems:
            logger.warning(
                f"⚠️ Failed to process {len(failed_stems)} stem(s): {', '.join(failed_stems)}"
            )
        else:
            logger.info(f"✅ All {len(stems_result)} stems processed successfully")

        if progress_callback:
            progress_callback(90, "All stems transcribed")

        # Step 2.5: Split MIDI files by instruments (NEW FEATURE)
        if progress_callback:
            progress_callback(91, "Splitting MIDI files by instruments...")

        from app.services.midi_processor import split_midi_by_instruments

        # For each successfully processed stem, split its MIDI file by instruments
        instruments_by_stem = {}  # stem_name -> [instrument_files]

        for stem_name, stem_result in stems_result.items():
            # Only split successful stems with MIDI files
            if stem_result.get('status') != 'failed' and stem_result.get('midi_path'):
                try:
                    midi_path = stem_result['midi_path']

                    # Create instruments subdirectory for this stem
                    instruments_dir = f"uploads/{job_id}/instruments/{stem_name}"
                    os.makedirs(instruments_dir, exist_ok=True)

                    # Split the stem MIDI into individual instrument files
                    instrument_files = split_midi_by_instruments(
                        midi_path=midi_path,
                        output_dir=instruments_dir,
                        stem_name=stem_name
                    )

                    # Store instrument files in stem result
                    instruments_by_stem[stem_name] = instrument_files
                    stem_result['instruments'] = instrument_files
                    stem_result['instruments_count'] = len(instrument_files)

                    logger.info(
                        f"✅ Split {stem_name} MIDI into {len(instrument_files)} instruments"
                    )

                except Exception as e:
                    logger.error(f"Failed to split {stem_name} MIDI by instruments: {e}")
                    # Non-critical error - continue without instrument splitting
                    stem_result['instruments'] = []
                    stem_result['instruments_count'] = 0
            else:
                stem_result['instruments'] = []
                stem_result['instruments_count'] = 0

        # Step 3: Calculate audio metadata (duration, tempo, beats)
        if progress_callback:
            progress_callback(92, "Calculating audio metadata...")

        try:
            import librosa
            import numpy as np

            # Load audio for analysis (use mono for faster processing)
            y, sr = librosa.load(audio_path, sr=22050, mono=True)

            # Calculate duration
            audio_duration = librosa.get_duration(y=y, sr=sr)

            # Detect tempo and beats
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)

            # Handle NaN tempo values
            tempo = float(tempo) if not np.isnan(tempo) else 0.0

            logger.info(
                f"Audio metadata: duration={audio_duration:.2f}s, tempo={tempo:.1f} BPM, beats={len(beat_times)}"
            )

        except Exception as e:
            logger.warning(f"Could not calculate metadata: {e}. Using defaults.")
            audio_duration = 0.0
            tempo = 0.0
            beat_times = []

        if progress_callback:
            progress_callback(95, "Compiling results...")

        # Step 4: Compile final result
        # Compile list of all unique instruments across all stems
        all_instruments = []
        instrument_families = set()

        for stem_name, instrument_list in instruments_by_stem.items():
            for inst in instrument_list:
                all_instruments.append({
                    "instrument_name": inst['instrument_name'],
                    "family": inst['family'],
                    "program": inst['program'],
                    "source_stem": stem_name,
                    "midi_filename": inst['midi_filename'],
                    "midi_path": inst['midi_path'],
                    "note_count": inst['note_count'],
                    "duration": inst['duration']
                })
                instrument_families.add(inst['family'])

        result = {
            "job_id": job_id,
            "song_info": {
                "filename": audio_file.name,
                "file_path": str(audio_file),
                "stems_separated": len(stem_paths),
                "duration": float(audio_duration),
                "tempo": float(tempo),
                "total_beats": int(len(beat_times)),
                "beats": [float(beat) for beat in beat_times] if len(beat_times) > 0 else []
            },
            "stems": stems_result,
            "instruments": all_instruments,  # NEW: All detected instruments
            "processing_summary": {
                "stems_processed": len(stems_result),
                "total_midi_files": sum(
                    1 for s in stems_result.values()
                    if s.get('midi_path') is not None
                ),
                "total_instruments": len(all_instruments),  # NEW
                "unique_families": sorted(list(instrument_families)),  # NEW
                "model": "YourMT3 (YPTF.MoE+Multi, 536M params)",
                "separator": "Demucs htdemucs (4-stem)"
            }
        }

        logger.info(f"Transcription completed successfully for job {job_id}")
        if progress_callback:
            progress_callback(100, "Transcription completed")

        return result

    except Exception as e:
        logger.error(f"Transcription failed for job {job_id}: {e}")
        if progress_callback:
            progress_callback(-1, f"Transcription failed: {str(e)}")
        raise RuntimeError(f"Transcription failed: {e}")


def transcribe_with_stems(
    audio_path: str,
    job_id: str,
    stems_to_process: Optional[list] = None,
    confidence_threshold: float = 0.1,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Transcribe audio with explicit stem selection

    Allows selecting specific stems for processing (useful for testing or optimization)

    Args:
        audio_path: Path to audio file
        job_id: Unique job identifier
        stems_to_process: List of stems to process ['bass', 'drums', 'other', 'vocals']
                         None = process all stems
        confidence_threshold: Minimum confidence for predictions
        progress_callback: Optional progress callback

    Returns:
        Analysis results dictionary (same format as transcribe_audio)

    Example:
        >>> # Only process bass and drums
        >>> result = transcribe_with_stems("song.mp3", "job-123", ['bass', 'drums'])
    """
    if stems_to_process is None:
        stems_to_process = ['bass', 'drums', 'other', 'vocals']

    logger.info(f"Transcribing with stems: {stems_to_process}")

    # Run full transcription
    result = transcribe_audio(
        audio_path=audio_path,
        job_id=job_id,
        confidence_threshold=confidence_threshold,
        progress_callback=progress_callback
    )

    # Filter results to only requested stems
    if 'stems' in result:
        result['stems'] = {
            stem: data for stem, data in result['stems'].items()
            if stem in stems_to_process
        }
        result['processing_summary']['stems_processed'] = len(result['stems'])

    return result


def get_transcription_stats(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract summary statistics from transcription result

    Args:
        result: Transcription result dictionary

    Returns:
        Dictionary with summary stats:
            - total_duration: Audio duration in seconds
            - tempo: Tempo in BPM (if available)
            - stems_processed: Number of stems processed
            - total_midi_files: Number of MIDI files generated
    """
    song_info = result.get('song_info', {})
    processing_summary = result.get('processing_summary', {})

    stats = {
        'total_duration': song_info.get('duration', 0),
        'total_beats': song_info.get('total_beats', 0),
        'tempo': song_info.get('tempo', 0),
        'stems_processed': processing_summary.get('stems_processed', 0),
        'total_segments': processing_summary.get('total_segments', 0),
        'total_midi_files': processing_summary.get('total_midi_files', 0)
    }

    return stats
