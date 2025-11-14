"""
Hybrid Transcription Service
Combines Demucs stem separation with MR-MT3 MIDI transcription

Pipeline:
1. Demucs separates audio → bass.wav, drums.wav, other.wav, vocals.wav
2. MR-MT3 transcribes full audio → fullmix.mid
3. Split fullmix.mid → per-instrument MIDI files
4. Return: stem WAVs + fullmix MIDI + instrument MIDIs + metadata
"""

import os
import logging
import librosa
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Callable

from app.services.demucs_separator import separate_stems, load_demucs_model
from app.services.mr_mt3_service import get_mr_mt3_service
from app.services.midi_processor import split_midi_by_instruments

logger = logging.getLogger(__name__)


def transcribe_audio_hybrid(
    audio_path: str,
    job_id: str,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Hybrid transcription pipeline: Demucs stems + MR-MT3 full audio transcription

    Pipeline Flow:
    1. Demucs stem separation (0-30%)
    2. MR-MT3 transcription on full audio (30-70%)
    3. MIDI instrument splitting (70-85%)
    4. Audio metadata calculation (85-95%)
    5. Results compilation (95-100%)

    Args:
        audio_path: Path to audio file (mp3, wav, flac, m4a)
        job_id: Unique job identifier for organizing outputs
        progress_callback: Optional callback function(progress: int, message: str)

    Returns:
        Dictionary containing:
            - song_info: Duration, tempo, beats, filename
            - stems: Stem WAV file paths (bass, drums, other, vocals)
            - fullmix_midi: Path to complete MIDI transcription
            - instruments: Detected instruments with individual MIDI files
            - processing_summary: Statistics about processing

    Raises:
        FileNotFoundError: If audio file not found
        RuntimeError: If any processing step fails
    """
    # Validate audio file exists
    audio_file = Path(audio_path)
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    logger.info(f"🎵 Starting HYBRID transcription pipeline for: {audio_path} (Job: {job_id})")

    if progress_callback:
        progress_callback(0, "Initializing hybrid pipeline...")

    try:
        # ================================================================
        # STEP 1: Demucs Stem Separation (0% → 30%)
        # ================================================================
        if progress_callback:
            progress_callback(5, "Separating audio into stems (Demucs)...")

        stems_dir = f"uploads/{job_id}/stems"
        os.makedirs(stems_dir, exist_ok=True)

        logger.info("Step 1: Running Demucs stem separation...")
        stem_paths = separate_stems(
            audio_path=audio_path,
            output_dir=stems_dir,
            model_name="htdemucs"  # 4-stem Demucs
        )

        # Create symlinks with job_id prefix for frontend compatibility
        # Frontend expects: {job_id}_bass.wav, {job_id}_drums.wav, etc.
        import shutil
        for stem_name, stem_path in list(stem_paths.items()):
            prefixed_filename = f"{job_id}_{stem_name}.wav"
            prefixed_path = os.path.join(stems_dir, prefixed_filename)

            try:
                if os.name != 'nt':  # Unix/Linux/Mac
                    if not os.path.exists(prefixed_path):
                        os.symlink(os.path.basename(stem_path), prefixed_path)
                else:  # Windows
                    if not os.path.exists(prefixed_path):
                        shutil.copy2(stem_path, prefixed_path)

                logger.debug(f"Created frontend path: {prefixed_filename}")
            except Exception as e:
                logger.warning(f"Could not create prefixed stem file: {e}")

        logger.info(f"✅ Demucs separation complete: {len(stem_paths)} stems created")

        if progress_callback:
            progress_callback(30, "Stem separation complete")

        # ================================================================
        # STEP 2: MR-MT3 Transcription on Full Audio (30% → 70%)
        # ================================================================
        if progress_callback:
            progress_callback(35, "Transcribing full audio with MR-MT3...")

        # Get MR-MT3 service
        mr_mt3_service = get_mr_mt3_service()
        if not mr_mt3_service.model_loaded:
            raise RuntimeError("MR-MT3 model not loaded")

        # Create MIDI output directory
        midi_dir = f"uploads/{job_id}/midi"
        os.makedirs(midi_dir, exist_ok=True)

        # Transcribe full audio to MIDI
        fullmix_midi_path = os.path.join(midi_dir, f"{job_id}_fullmix.mid")

        logger.info("Step 2: Running MR-MT3 transcription on full audio...")
        mr_mt3_service.transcribe_audio(
            audio_path=audio_path,
            output_path=fullmix_midi_path
        )

        if not os.path.exists(fullmix_midi_path):
            raise FileNotFoundError(f"MR-MT3 did not create MIDI file: {fullmix_midi_path}")

        logger.info(f"✅ MR-MT3 transcription complete: {fullmix_midi_path}")

        if progress_callback:
            progress_callback(70, "Full audio transcribed to MIDI")

        # ================================================================
        # STEP 3: Split MIDI by Instruments (70% → 85%)
        # ================================================================
        if progress_callback:
            progress_callback(72, "Detecting and splitting instruments...")

        # Create instruments directory
        instruments_dir = f"uploads/{job_id}/instruments"
        os.makedirs(instruments_dir, exist_ok=True)

        logger.info("Step 3: Splitting MIDI by detected instruments...")
        try:
            instrument_files = split_midi_by_instruments(
                midi_path=fullmix_midi_path,
                output_dir=instruments_dir,
                stem_name="fullmix"
            )

            logger.info(f"✅ MIDI split complete: {len(instrument_files)} instruments detected")

        except Exception as e:
            logger.error(f"Failed to split MIDI by instruments: {e}")
            instrument_files = []

        if progress_callback:
            progress_callback(85, f"Detected {len(instrument_files)} instruments")

        # ================================================================
        # STEP 4: Calculate Audio Metadata (85% → 95%)
        # ================================================================
        if progress_callback:
            progress_callback(87, "Calculating audio metadata...")

        logger.info("Step 4: Calculating audio metadata (duration, tempo, beats)...")
        try:
            # Load audio for analysis
            y, sr = librosa.load(audio_path, sr=22050, mono=True)

            # Calculate duration
            audio_duration = librosa.get_duration(y=y, sr=sr)

            # Detect tempo and beats
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)

            # Handle NaN tempo values
            tempo = float(tempo) if not np.isnan(tempo) else 0.0

            logger.info(
                f"Audio metadata: duration={audio_duration:.2f}s, "
                f"tempo={tempo:.1f} BPM, beats={len(beat_times)}"
            )

        except Exception as e:
            logger.warning(f"Could not calculate metadata: {e}. Using defaults.")
            audio_duration = 0.0
            tempo = 0.0
            beat_times = []

        if progress_callback:
            progress_callback(95, "Compiling final results...")

        # ================================================================
        # STEP 5: Compile Final Results (95% → 100%)
        # ================================================================
        logger.info("Step 5: Compiling final results...")

        # Build stems result with WAV paths
        stems_result = {}
        for stem_name, stem_path in stem_paths.items():
            stems_result[stem_name] = {
                "type": "audio",
                "stem": stem_name,
                "audio_path": stem_path,
                "audio_url": f"/files/{job_id}_{stem_name}.wav",
                "status": "processed"
            }

        # Build instruments list with metadata
        all_instruments = []
        instrument_families = set()

        for inst in instrument_files:
            all_instruments.append({
                "instrument_name": inst['instrument_name'],
                "family": inst['family'],
                "program": inst['program'],
                "midi_filename": inst['midi_filename'],
                "midi_path": inst['midi_path'],
                "midi_url": f"/files/instruments/{inst['midi_filename']}",
                "note_count": inst['note_count'],
                "duration": inst['duration'],
                "is_drum": inst.get('is_drum', False)
            })
            instrument_families.add(inst['family'])

        # Build final result
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
            "fullmix_midi": {
                "midi_path": fullmix_midi_path,
                "midi_url": f"/files/{job_id}_fullmix.mid",
                "midi_filename": f"{job_id}_fullmix.mid"
            },
            "instruments": all_instruments,
            "processing_summary": {
                "stems_processed": len(stem_paths),
                "total_instruments": len(all_instruments),
                "unique_families": sorted(list(instrument_families)),
                "fullmix_midi_generated": True,
                "model": "MR-MT3 (Memory Retaining Multi-Track Music Transcription)",
                "separator": "Demucs htdemucs (4-stem)",
                "pipeline": "hybrid"
            }
        }

        logger.info(
            f"✅ Hybrid transcription pipeline complete for job {job_id}: "
            f"{len(stem_paths)} stems, {len(all_instruments)} instruments detected"
        )

        if progress_callback:
            progress_callback(100, "Transcription complete")

        return result

    except Exception as e:
        logger.error(f"❌ Hybrid transcription failed for job {job_id}: {e}")
        if progress_callback:
            progress_callback(-1, f"Transcription failed: {str(e)}")
        raise RuntimeError(f"Hybrid transcription failed: {e}")


def preload_models():
    """
    Preload Demucs and MR-MT3 models for faster processing

    Call this during service initialization to avoid delays
    on the first transcription request.
    """
    try:
        logger.info("Preloading models for hybrid pipeline...")

        # Preload Demucs
        load_demucs_model("htdemucs")
        logger.info("✅ Demucs model preloaded")

        # Preload MR-MT3
        mr_mt3_service = get_mr_mt3_service()
        if mr_mt3_service.model_loaded:
            logger.info("✅ MR-MT3 model preloaded")
        else:
            logger.warning("⚠️ MR-MT3 model not loaded")

        logger.info("✅ All models preloaded for hybrid pipeline")

    except Exception as e:
        logger.error(f"Failed to preload models: {e}")
        raise
