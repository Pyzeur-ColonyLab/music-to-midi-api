"""
YourMT3 Integration Service
Handles model loading and MIDI transcription using YourMT3
"""

import os
import sys
from pathlib import Path
import torch
import torchaudio
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

# YourMT3 paths
# We now use a local copy of amt/ in the working directory
API_ROOT = Path(__file__).resolve().parents[2]  # music-to-midi-api/
YOURMT3_PATH = API_ROOT / "amt"  # Local amt directory
YOURMT3_SRC_PATH = YOURMT3_PATH / "src"  # amt/src for module imports

# YourMT3 modules (imported lazily)
_yourmt3_modules_loaded = False

# Global model instance (singleton pattern for efficiency)
_yourmt3_model: Optional[Any] = None


def _ensure_yourmt3_modules():
    """
    Load YourMT3 modules on-demand (lazy loading)

    This avoids sys.path conflicts at import time by only adding
    YourMT3 paths when we actually need to use the model.
    """
    global _yourmt3_modules_loaded

    if _yourmt3_modules_loaded:
        return

    logger.info("Loading YourMT3 modules...")

    # Add YourMT3 paths to sys.path for model imports
    # Need both amt/ (for model_helper.py) and amt/src/ (for model modules)
    if str(YOURMT3_PATH) not in sys.path:
        sys.path.insert(0, str(YOURMT3_PATH))
        logger.debug(f"Added to sys.path: {YOURMT3_PATH}")

    if str(YOURMT3_SRC_PATH) not in sys.path:
        sys.path.insert(0, str(YOURMT3_SRC_PATH))
        logger.debug(f"Added to sys.path: {YOURMT3_SRC_PATH}")

    # Import YourMT3 modules
    try:
        global load_model_checkpoint, transcribe, Timer
        from model_helper import load_model_checkpoint, transcribe
        from utils.utils import Timer

        _yourmt3_modules_loaded = True
        logger.info("YourMT3 modules loaded successfully")

    except ImportError as e:
        raise ImportError(
            f"Failed to import YourMT3 modules. Ensure amt/ directory exists.\n"
            f"Expected path: {YOURMT3_SRC_PATH}\n"
            f"Error: {e}"
        )


def load_yourmt3(
    checkpoint_name: str = "mc13_256_g4_all_v7_mt3f_sqr_rms_moe_wf4_n8k2_silu_rope_rp_b36_nops@last.ckpt",
    device: Optional[str] = None
) -> Any:
    """
    Load YourMT3 model from checkpoint

    Args:
        checkpoint_name: Checkpoint identifier (name@last.ckpt format)
        device: Device to use ('cuda', 'cpu', or None for auto-detect)

    Returns:
        Loaded YourMT3 model in eval mode

    Raises:
        RuntimeError: If model loading fails
    """
    global _yourmt3_model

    # Ensure YourMT3 modules are loaded
    _ensure_yourmt3_modules()

    # Auto-detect device if not specified
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Auto-detected device: {device}")

    logger.info(f"🎹 Loading YourMT3 model...")
    logger.info(f"   Checkpoint: {checkpoint_name}")
    logger.info(f"   Device: {device}")

    try:
        # Parse checkpoint arguments from name
        # Format: mc13_256_g4_all_v7_mt3f_sqr_rms_moe_wf4_n8k2_silu_rope_rp_b36_nops@last.ckpt
        args = [
            checkpoint_name,
            '-p', '2024',
            '-tk', 'mc13_full_plus_256',
            '-dec', 'multi-t5',
            '-nl', '26',
            '-enc', 'perceiver-tf',
            '-sqr', '1',
            '-ff', 'moe',
            '-wf', '4',
            '-nmoe', '8',
            '-kmoe', '2',
            '-act', 'silu',
            '-epe', 'rope',
            '-rp', '1',
            '-ac', 'spec',
            '-hop', '300',
            '-atc', '1',
            '-pr', '16'
        ]

        # YourMT3 expects to be run from its directory for checkpoint loading
        # Since checkpoint path is hardcoded as "amt/logs/...", we need to cd to API root
        original_cwd = os.getcwd()
        os.chdir(API_ROOT)
        logger.debug(f"Changed working directory to: {API_ROOT}")

        try:
            # Load model using YourMT3's load_model_checkpoint
            model = load_model_checkpoint(args=args, device=device)
        finally:
            # Always restore original working directory
            os.chdir(original_cwd)
            logger.debug(f"Restored working directory to: {original_cwd}")

        # Cache instance for reuse
        _yourmt3_model = model

        logger.info("✅ YourMT3 model loaded successfully")
        return model

    except Exception as e:
        logger.error(f"❌ Failed to load YourMT3 model: {e}")
        raise RuntimeError(f"YourMT3 model loading failed: {e}")


def get_yourmt3_model() -> Optional[Any]:
    """
    Get cached YourMT3 model instance

    Returns:
        Cached model instance or None if not loaded
    """
    return _yourmt3_model


def transcribe_audio_to_midi(
    audio_path: str,
    output_dir: str,
    track_name: str,
    model: Optional[Any] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Transcribe audio file to MIDI using YourMT3

    Args:
        audio_path: Path to audio file (stem or full track)
        output_dir: Directory to save MIDI file
        track_name: Name for output MIDI file (without .mid extension)
        model: YourMT3 model instance (uses cached if None)

    Returns:
        Tuple of (midi_path, transcription_stats)

    Raises:
        RuntimeError: If transcription fails
        FileNotFoundError: If audio file not found
    """
    # Ensure YourMT3 modules are loaded
    _ensure_yourmt3_modules()

    # Validate audio file exists
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Use cached model if not provided
    if model is None:
        model = get_yourmt3_model()
        if model is None:
            raise RuntimeError(
                "YourMT3 model not loaded. Call load_yourmt3() first."
            )

    # Create output directory if needed
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"🎵 Transcribing: {audio_path}")
    logger.info(f"   Output: {output_dir}/{track_name}.mid")

    try:
        # Get audio info
        info = torchaudio.info(audio_path)

        # Prepare audio info dict for YourMT3 transcribe function
        audio_info = {
            "filepath": audio_path,
            "track_name": track_name,
            "sample_rate": info.sample_rate,
            "num_frames": info.num_frames,
            "num_channels": info.num_channels,
            "bits_per_sample": info.bits_per_sample if hasattr(info, 'bits_per_sample') else None,
            "encoding": str(info.encoding) if hasattr(info, 'encoding') else None
        }

        # Change working directory temporarily for YourMT3 output
        original_cwd = os.getcwd()
        os.chdir(output_dir)

        try:
            # Transcribe using YourMT3
            midi_path = transcribe(model, audio_info)

            # Move MIDI file to proper location if needed
            # YourMT3 outputs to ./model_output/{track_name}.mid
            yourmt3_output = os.path.join(output_dir, 'model_output', f'{track_name}.mid')
            final_midi_path = os.path.join(output_dir, f'{track_name}.mid')

            if os.path.exists(yourmt3_output) and yourmt3_output != final_midi_path:
                os.makedirs(os.path.dirname(final_midi_path), exist_ok=True)
                os.rename(yourmt3_output, final_midi_path)
                midi_path = final_midi_path

        finally:
            # Restore working directory
            os.chdir(original_cwd)

        # Get basic stats from MIDI file
        transcription_stats = {
            'audio_path': audio_path,
            'midi_path': midi_path,
            'track_name': track_name,
            'sample_rate': info.sample_rate,
            'duration_seconds': info.num_frames / info.sample_rate,
            'success': True
        }

        logger.info(f"✅ Transcription complete: {midi_path}")
        return midi_path, transcription_stats

    except Exception as e:
        logger.error(f"❌ Transcription failed: {e}")
        raise RuntimeError(f"Audio transcription failed: {e}")


def get_model_info() -> Dict[str, Any]:
    """
    Get information about loaded YourMT3 model

    Returns:
        Dictionary with model metadata

    Raises:
        RuntimeError: If model not loaded
    """
    if _yourmt3_model is None:
        raise RuntimeError("YourMT3 model not loaded. Call load_yourmt3() first.")

    model_info = {
        'model_name': 'YourMT3',
        'version': 'YPTF.MoE+Multi',
        'parameters': '536M',
        'checkpoint': 'mc13_256_g4_all_v7_mt3f_sqr_rms_moe_wf4_n8k2_silu_rope_rp_b36_nops',
        'device': str(_yourmt3_model.device) if hasattr(_yourmt3_model, 'device') else 'unknown',
        'capabilities': [
            'audio_to_midi_transcription',
            'multi_instrument_support',
            'polyphonic_transcription',
            'percussion_transcription'
        ],
        'input_formats': ['wav', 'mp3', 'flac', 'ogg'],
        'output_format': 'MIDI Type 0',
        'sample_rate': 16000,  # YourMT3 default
        'max_polyphony': 'unlimited',
        'latency': 'medium (~30s for 1min audio on CPU)'
    }

    return model_info


def unload_model():
    """
    Unload YourMT3 model from memory
    Useful for testing or memory management
    """
    global _yourmt3_model

    if _yourmt3_model is not None:
        logger.info("Unloading YourMT3 model from memory")
        _yourmt3_model = None

        # Force garbage collection
        import gc
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
