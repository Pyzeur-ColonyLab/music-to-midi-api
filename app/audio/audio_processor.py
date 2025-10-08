"""
Audio Processing Pipeline
Implements beat detection, Demucs stem separation, and instrument classification
Updated to work with 99.38% accuracy YAMNet model from working notebook
"""

import librosa
import numpy as np
import torch
import torchaudio
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Callable
import tempfile
import os
import subprocess
import shutil

# Use Demucs via subprocess (command-line interface)
DEMUCS_ENV_PATH = Path(__file__).parent.parent.parent / "demucs" / "Spleeter_Music" / "demucs_env"
DEMUCS_PYTHON = DEMUCS_ENV_PATH / "bin" / "python3"

if DEMUCS_ENV_PATH.exists() and DEMUCS_PYTHON.exists():
    DEMUCS_AVAILABLE = True
    DEMUCS_COMMAND = str(DEMUCS_PYTHON)
    print(f"✅ Local Demucs environment found: {DEMUCS_ENV_PATH}")
else:
    # Check for system/venv demucs installation
    demucs_path = shutil.which("demucs")
    if demucs_path:
        DEMUCS_AVAILABLE = True
        DEMUCS_COMMAND = "demucs"  # Use demucs command directly
        print(f"✅ Demucs installation found: {demucs_path}")
    else:
        DEMUCS_AVAILABLE = False
        print("❌ WARNING: Demucs not available!")
        print("Install with: pip install demucs")
        # Don't raise error at import time - let it fail gracefully later if needed

# Import the correct model
try:
    from models.yamnet_classifier import get_classifier
    YAMNET_AVAILABLE = True
except ImportError:
    YAMNET_AVAILABLE = False
    logging.warning("YAMNet production model not available")

logger = logging.getLogger(__name__)

class AudioProcessingPipeline:
    """Complete audio processing pipeline for instrument recognition"""

    def __init__(self, sample_rate: int = 22050, segment_duration: float = 4.0,
                 use_stem_separation: bool = True):
        self.sample_rate = sample_rate
        self.segment_duration = segment_duration
        self.use_stem_separation = use_stem_separation
        self.demucs_model = None
        self.classifier = None

        # Initialize Demucs model - only if stem separation is enabled
        if self.use_stem_separation:
            self._initialize_demucs_model()
        else:
            logger.info("🚫 Stem separation disabled - using mixed audio only")

        # Initialize YAMNet classifier if available
        if YAMNET_AVAILABLE:
            try:
                model_path = "models/yamnet_instrument_classifier_production.pth"
                metadata_path = "models/model_metadata.json"

                # Check if model files exist
                if Path(model_path).exists() and Path(metadata_path).exists():
                    self.classifier = get_classifier()
                    logger.info(f"✅ YAMNet classifier loaded with {self.classifier.metadata['best_validation_accuracy']:.2f}% accuracy")
                else:
                    logger.warning(f"Model files not found - YAMNet classifier disabled")
                    logger.warning(f"  Expected: {model_path} and {metadata_path}")
            except Exception as e:
                logger.warning(f"Failed to load YAMNet classifier: {e}")
                self.classifier = None
        else:
            logger.warning("YAMNet production model not available - classification disabled")

    def load_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """Load audio file and return audio data and sample rate"""
        try:
            # Use librosa for robust audio loading
            audio, sr = librosa.load(audio_path, sr=None, mono=False)

            # Convert to mono if stereo
            if audio.ndim > 1:
                audio = librosa.to_mono(audio)

            logger.info(f"Loaded audio: {len(audio)/sr:.2f}s at {sr}Hz")
            return audio, sr

        except Exception as e:
            logger.error(f"Error loading audio file {audio_path}: {e}")
            raise

    def detect_beats(self, audio: np.ndarray, sr: int) -> Tuple[np.ndarray, float]:
        """Detect beats and estimate tempo with improved accuracy"""
        try:
            # Method 1: Standard beat tracking
            tempo1, beat_frames1 = librosa.beat.beat_track(
                y=audio,
                sr=sr,
                units='frames',
                trim=False
            )

            # Method 2: Onset-based beat tracking with better parameters
            onset_envelope = librosa.onset.onset_strength(y=audio, sr=sr)
            tempo2, beat_frames2 = librosa.beat.beat_track(
                onset_envelope=onset_envelope,
                sr=sr,
                units='frames',
                trim=False,
                start_bpm=120,  # Better starting point
                tightness=200   # More consistent tempo
            )

            # Method 3: Tempogram-based analysis for better tempo estimation
            try:
                hop_length = 512
                tempogram = librosa.feature.tempogram(
                    onset_envelope=onset_envelope,
                    sr=sr,
                    hop_length=hop_length
                )
                # Get tempo from tempogram
                tempo_freqs = librosa.tempo_frequencies(n_bins=tempogram.shape[0], sr=sr, hop_length=hop_length)
                tempo3 = tempo_freqs[np.argmax(np.mean(tempogram, axis=1))]
            except:
                tempo3 = tempo2

            # Choose the most reasonable tempo (typically between 80-200 BPM for most music)
            tempos = [tempo1, tempo2, tempo3]
            valid_tempos = [t for t in tempos if 80 <= t <= 200]

            if valid_tempos:
                # Use the tempo closest to common dance music tempos (120-140)
                final_tempo = min(valid_tempos, key=lambda x: abs(x - 128))

                # Use beat frames from the method that gave us the final tempo
                if abs(final_tempo - tempo1) < 1:
                    beat_frames = beat_frames1
                elif abs(final_tempo - tempo2) < 1:
                    beat_frames = beat_frames2
                else:
                    beat_frames = beat_frames2  # Default to method 2
            else:
                # Fallback to method 2 if no valid tempos
                final_tempo = tempo2
                beat_frames = beat_frames2

            # Convert frames to time
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)

            # Validate beat consistency - remove if beats are too close or far apart
            if len(beat_times) > 1:
                beat_intervals = np.diff(beat_times)
                expected_interval = 60.0 / final_tempo

                # Remove beats that are too close (less than 50% of expected interval)
                # or too far (more than 150% of expected interval)
                valid_beat_mask = np.ones(len(beat_times), dtype=bool)
                for i in range(1, len(beat_times)):
                    interval = beat_times[i] - beat_times[i-1]
                    if interval < 0.5 * expected_interval or interval > 1.5 * expected_interval:
                        if i < len(beat_times) - 1:  # Don't remove the last beat
                            valid_beat_mask[i] = False

                beat_times = beat_times[valid_beat_mask]

            logger.info(f"Detected {len(beat_times)} beats at {float(final_tempo):.1f} BPM")
            logger.info(f"Tempo analysis: Method1={float(tempo1):.1f}, Method2={float(tempo2):.1f}, Method3={float(tempo3):.1f}, Final={float(final_tempo):.1f}")

            return beat_times, float(final_tempo)

        except Exception as e:
            logger.error(f"Error detecting beats: {e}")
            import traceback
            traceback.print_exc()

            # More intelligent fallback - try to estimate from audio length and common BPMs
            duration = len(audio) / sr
            # For 6.8 minute song, if it's 128 BPM, we'd expect ~870 beats
            if duration > 300:  # Long song, likely dance/electronic
                bpm = 128.0
            else:
                bpm = 120.0

            beat_interval = 60.0 / bpm
            beat_times = np.arange(0, duration, beat_interval)
            logger.warning(f"Beat detection failed, using fallback: {bpm} BPM with {len(beat_times)} beats")
            return beat_times, bpm

    def separate_stems(self, audio: np.ndarray, sr: int) -> Dict[str, np.ndarray]:
        """Separate audio into stems using Demucs via subprocess or use mixed audio"""

        # If stem separation is disabled, return the same audio for all stems
        if not self.use_stem_separation:
            logger.info("🎵 Using mixed audio for all stems (no separation)")
            stems = {
                'drums': audio.copy(),
                'bass': audio.copy(),
                'other': audio.copy(),
                'vocals': audio.copy()
            }
            logger.info(f"✅ Mixed audio duplicated to 4 stems: {list(stems.keys())}")
            return stems

        # Original stem separation logic
        if not DEMUCS_AVAILABLE:
            error_msg = "❌ CRITICAL: Demucs not available! Stem separation is mandatory when use_stem_separation=True."
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            logger.info(f"🎵 Starting Demucs stem separation on {len(audio)/sr:.1f}s audio...")

            # Create temporary directory for processing
            with tempfile.TemporaryDirectory(prefix="demucs_") as temp_dir:
                temp_path = Path(temp_dir)

                # Save input audio to temporary file
                input_file = temp_path / "input.wav"
                logger.info(f"💾 Saving audio to {input_file}")

                # Convert mono to stereo if needed for Demucs
                if audio.ndim == 1:
                    # Duplicate mono channel to create stereo
                    stereo_audio = np.stack([audio, audio])
                else:
                    stereo_audio = audio

                # Save as WAV file at original sample rate
                torchaudio.save(str(input_file), torch.from_numpy(stereo_audio), sr)

                # Run Demucs separation via subprocess
                logger.info("🔄 Running Demucs stem separation via subprocess...")
                if DEMUCS_COMMAND == "demucs":
                    # Use direct demucs command
                    cmd = [
                        DEMUCS_COMMAND,
                        "-o", str(temp_path),
                        str(input_file)
                    ]
                else:
                    # Use python -m demucs.separate for custom env
                    cmd = [
                        DEMUCS_COMMAND, "-m", "demucs.separate",
                        "--out", str(temp_path),
                        str(input_file)
                    ]

                logger.info(f"Running command: {' '.join(cmd)}")

                # Run the command
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=900  # 15 minute timeout
                )

                if result.returncode != 0:
                    error_msg = f"❌ Demucs command failed (code {result.returncode}): {result.stderr}"
                    logger.error(error_msg)
                    logger.error(f"Command stdout: {result.stdout}")
                    raise RuntimeError(error_msg)

                logger.info("✅ Demucs subprocess completed successfully")
                logger.info(f"Demucs output: {result.stdout}")

                # Find the output directory (Demucs creates htdemucs/input/)
                output_base = temp_path / "htdemucs" / "input"
                if not output_base.exists():
                    # Try alternative directory structure
                    output_base = temp_path / "separated" / "htdemucs" / "input"
                    if not output_base.exists():
                        error_msg = f"❌ Demucs output directory not found. Expected: {output_base}"
                        logger.error(error_msg)
                        # List what was created
                        logger.error(f"Available files: {list(temp_path.rglob('*'))}")
                        raise RuntimeError(error_msg)

                # Load the separated stems
                stem_names = ['drums', 'bass', 'other', 'vocals']
                separated_stems = {}

                for stem_name in stem_names:
                    stem_file = output_base / f"{stem_name}.wav"
                    if stem_file.exists():
                        logger.info(f"📂 Loading {stem_name} from {stem_file}")

                        # Load the stem audio
                        stem_audio, stem_sr = torchaudio.load(str(stem_file))
                        stem_audio = stem_audio.numpy()

                        # Convert stereo to mono by averaging channels
                        if stem_audio.ndim > 1 and stem_audio.shape[0] > 1:
                            stem_audio = np.mean(stem_audio, axis=0)
                        elif stem_audio.ndim > 1:
                            stem_audio = stem_audio[0]  # Take first channel

                        # Resample if needed
                        if stem_sr != sr:
                            logger.info(f"Resampling {stem_name} from {stem_sr}Hz to {sr}Hz")
                            stem_tensor = torch.from_numpy(stem_audio).float()
                            resampler = torchaudio.transforms.Resample(stem_sr, sr)
                            stem_audio = resampler(stem_tensor).numpy()

                        separated_stems[stem_name] = stem_audio

                        # Log stem quality
                        rms_energy = np.sqrt(np.mean(stem_audio**2))
                        logger.info(f"  ✅ {stem_name} stem: RMS energy = {rms_energy:.4f}")
                    else:
                        error_msg = f"❌ Expected stem file not found: {stem_file}"
                        logger.error(error_msg)
                        logger.error(f"Available files: {list(output_base.glob('*.wav'))}")
                        raise RuntimeError(error_msg)

                if len(separated_stems) != 4:
                    error_msg = f"❌ Expected 4 stems, got {len(separated_stems)}. Demucs separation failed."
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

                logger.info(f"✅ Demucs separation completed successfully: {list(separated_stems.keys())}")
                return separated_stems

        except subprocess.TimeoutExpired:
            error_msg = "❌ CRITICAL: Demucs process timed out after 15 minutes"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            logger.error(f"❌ CRITICAL: Demucs stem separation failed: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"Demucs separation is mandatory but failed: {e}")

    def _initialize_demucs_model(self):
        """Initialize Demucs command - called during pipeline initialization"""
        if not DEMUCS_AVAILABLE:
            error_msg = "❌ CRITICAL: Cannot initialize - Demucs not available!"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            # Test Demucs command
            logger.info("🔄 Testing Demucs installation...")

            # Test command
            if DEMUCS_COMMAND == "demucs":
                cmd = [DEMUCS_COMMAND, "--help"]
            else:
                cmd = [DEMUCS_COMMAND, "-m", "demucs.separate", "--help"]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                self.demucs_model = "htdemucs"  # Use htdemucs by default
                logger.info("✅ Demucs command-line interface working")
            else:
                raise RuntimeError(f"Demucs test failed: {result.stderr}")

        except Exception as e:
            error_msg = f"❌ CRITICAL: Failed to initialize Demucs: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    def segment_audio_by_beats(self, audio: np.ndarray, beat_times: np.ndarray, sr: int) -> List[Dict[str, Any]]:
        """Segment audio by beat-aligned windows"""
        segments = []
        target_samples = int(self.segment_duration * sr)

        for i, beat_start in enumerate(beat_times):
            # Calculate segment boundaries
            start_time = beat_start
            end_time = start_time + self.segment_duration

            # Convert to sample indices
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)

            # Extract segment
            if end_sample <= len(audio):
                segment = audio[start_sample:end_sample]
            else:
                # Pad if needed
                segment = audio[start_sample:]
                padding = target_samples - len(segment)
                segment = np.pad(segment, (0, padding), mode='constant')

            # Ensure correct length
            if len(segment) > target_samples:
                segment = segment[:target_samples]
            elif len(segment) < target_samples:
                padding = target_samples - len(segment)
                segment = np.pad(segment, (0, padding), mode='constant')

            segments.append({
                'beat_id': i,
                'start_time': start_time,
                'end_time': end_time,
                'audio': segment,
                'duration': self.segment_duration
            })

        logger.info(f"Created {len(segments)} beat-aligned segments")
        return segments

    def classify_segments(self, segments: List[Dict[str, Any]], progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """Classify instruments in audio segments using the production YAMNet model"""
        if self.classifier is None:
            logger.warning("No classifier available - returning empty predictions")
            classified_segments = []
            for segment in segments:
                classified_segments.append({
                    **segment,
                    'predictions': {},
                    'top_instrument': 'unknown',
                    'confidence': 0.0
                })
            return classified_segments

        classified_segments = []
        total_segments = len(segments)

        try:
            for i, segment in enumerate(segments):
                if progress_callback and i % 10 == 0:  # Update progress every 10 segments
                    progress = int(80 + (i / total_segments) * 15)  # Progress from 80% to 95%
                    progress_callback(progress, f"Classifying segment {i+1}/{total_segments}...")

                # Convert numpy array to torch tensor
                audio_data = segment['audio']
                audio_tensor = torch.from_numpy(audio_data).float()

                # Get predictions from the production classifier
                predictions = self.classifier.predict_segment(audio_tensor)

                # Find top prediction
                top_instrument = max(predictions.items(), key=lambda x: x[1])

                classified_segment = {
                    **segment,
                    'predictions': predictions,
                    'top_instrument': top_instrument[0],
                    'confidence': top_instrument[1]
                }

                classified_segments.append(classified_segment)

            logger.info(f"Classified {len(classified_segments)} segments using YAMNet model")

        except Exception as e:
            logger.error(f"Error during classification: {e}")
            # Fallback: return segments without classification
            for segment in segments:
                classified_segments.append({
                    **segment,
                    'predictions': {},
                    'top_instrument': 'unknown',
                    'confidence': 0.0
                })

        return classified_segments

    def process_audio_file(self, audio_path: str, progress_callback=None) -> Dict[str, Any]:
        """Complete audio processing pipeline"""
        try:
            if progress_callback:
                progress_callback(5, "Loading audio file...")

            # Step 1: Load audio
            audio, original_sr = self.load_audio(audio_path)

            if progress_callback:
                progress_callback(15, "Detecting beats...")

            # Step 2: Beat detection
            beat_times, bpm = self.detect_beats(audio, original_sr)

            if progress_callback:
                progress_callback(25, "Separating stems with Demucs...")

            # Step 3: Stem separation
            stems = self.separate_stems(audio, original_sr)

            if progress_callback:
                progress_callback(50, "Creating beat-aligned segments...")

            # Step 4: Resample to target sample rate
            if original_sr != self.sample_rate:
                resampler = torchaudio.transforms.Resample(original_sr, self.sample_rate)
                for stem_name in stems:
                    stem_tensor = torch.from_numpy(stems[stem_name]).float()
                    stems[stem_name] = resampler(stem_tensor).numpy()

                # Also resample beat detection result
                audio_resampled = resampler(torch.from_numpy(audio).float()).numpy()
                beat_times_resampled, _ = self.detect_beats(audio_resampled, self.sample_rate)
                beat_times = beat_times_resampled

            if progress_callback:
                progress_callback(60, "Segmenting audio by beats...")

            # Step 5: Create beat-aligned segments for each stem
            processed_stems = {}
            for stem_name, stem_audio in stems.items():
                segments = self.segment_audio_by_beats(stem_audio, beat_times, self.sample_rate)
                processed_stems[stem_name] = segments

            if progress_callback:
                progress_callback(75, "Classifying instruments with YAMNet model...")

            # Step 6: Classify segments using the production YAMNet model
            if self.use_stem_separation:
                # Normal stem-based classification
                classified_stems = {}
                for stem_name, segments in processed_stems.items():
                    if progress_callback:
                        progress_callback(75, f"Classifying {stem_name} segments...")

                    classified_segments = self.classify_segments(segments, progress_callback)
                    classified_stems[stem_name] = classified_segments

                total_segments = len(classified_stems['drums']) if 'drums' in classified_stems else 0
                classification_key = 'stems'
                classification_data = classified_stems
            else:
                # No-stems mode: classify mixed audio once
                if progress_callback:
                    progress_callback(75, "Classifying mixed audio segments...")

                # Use any stem's segments (they're all identical mixed audio)
                mixed_segments = list(processed_stems.values())[0]
                classified_segments = self.classify_segments(mixed_segments, progress_callback)

                total_segments = len(classified_segments)
                classification_key = 'segments'
                classification_data = classified_segments

            if progress_callback:
                progress_callback(95, "Finalizing processing...")

            # Calculate total duration
            duration = len(audio) / original_sr

            result = {
                'file_info': {
                    'duration': duration,
                    'original_sample_rate': original_sr,
                    'target_sample_rate': self.sample_rate,
                    'bpm': bpm,
                    'total_beats': len(beat_times)
                },
                'beat_times': beat_times.tolist(),
                classification_key: classification_data,  # Either 'stems' or 'segments'
                'processing_info': {
                    'demucs_available': DEMUCS_AVAILABLE and self.demucs_model is not None,
                    'stem_separation_used': self.use_stem_separation,
                    'yamnet_available': YAMNET_AVAILABLE and self.classifier is not None,
                    'segment_duration': self.segment_duration,
                    'total_segments_per_stem': total_segments,
                    'model_accuracy': self.classifier.metadata['best_validation_accuracy'] if self.classifier else None
                }
            }

            if progress_callback:
                progress_callback(90, "Audio processing complete")

            logger.info(f"Audio processing complete: {duration:.1f}s, {len(beat_times)} beats, {bpm:.1f} BPM")
            return result

        except Exception as e:
            logger.error(f"Error in audio processing pipeline: {e}")
            if progress_callback:
                progress_callback(-1, f"Processing failed: {str(e)}")
            raise

# Global pipeline instance
_pipeline_instance: Optional[AudioProcessingPipeline] = None

def get_audio_pipeline() -> AudioProcessingPipeline:
    """Get singleton audio pipeline instance"""
    global _pipeline_instance

    if _pipeline_instance is None:
        _pipeline_instance = AudioProcessingPipeline()

    return _pipeline_instance

def initialize_audio_pipeline(sample_rate: int = 22050, segment_duration: float = 4.0) -> AudioProcessingPipeline:
    """Initialize audio pipeline with specific parameters"""
    global _pipeline_instance

    _pipeline_instance = AudioProcessingPipeline(
        sample_rate=sample_rate,
        segment_duration=segment_duration
    )

    return _pipeline_instance