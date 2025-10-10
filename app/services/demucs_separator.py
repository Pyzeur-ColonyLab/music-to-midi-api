"""
Demucs Stem Separation Service
Separates audio into stems (bass, drums, other, vocals) using Demucs
"""

import os
import logging
import torch
import torchaudio
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Demucs modules (imported directly from pip package)
_demucs_modules_loaded = False

# Global model cache
_demucs_model: Optional[any] = None


def _ensure_demucs_modules():
    """
    Load Demucs modules on-demand (lazy loading)

    Uses pip-installed demucs package
    """
    global _demucs_modules_loaded

    if _demucs_modules_loaded:
        return

    logger.info("Loading Demucs modules...")

    # Import Demucs modules from pip package
    try:
        global get_model, apply_model
        from demucs.pretrained import get_model
        from demucs.apply import apply_model

        _demucs_modules_loaded = True
        logger.info("Demucs modules loaded successfully")

    except ImportError as e:
        raise ImportError(
            f"Failed to import Demucs modules. Install with: pip install demucs\n"
            f"Error: {e}"
        )


def load_demucs_model(model_name: str = "htdemucs") -> any:
    """
    Load Demucs model for stem separation

    Args:
        model_name: Demucs model name
                   - "htdemucs": Hybrid Transformer Demucs (4-stem: vocals, drums, bass, other)
                   - "htdemucs_ft": Fine-tuned version
                   - "mdx_extra": Extra quality model

    Returns:
        Loaded Demucs model

    Raises:
        RuntimeError: If model loading fails
    """
    global _demucs_model

    # Ensure Demucs modules are loaded
    _ensure_demucs_modules()

    logger.info(f"Loading Demucs model: {model_name}")

    try:
        model = get_model(model_name)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device)
        model.eval()

        _demucs_model = model

        logger.info(f"✅ Demucs model loaded: {model_name} on {device}")
        return model

    except Exception as e:
        logger.error(f"❌ Failed to load Demucs model: {e}")
        raise RuntimeError(f"Demucs model loading failed: {e}")


def get_demucs_model() -> Optional[any]:
    """
    Get cached Demucs model instance

    Returns:
        Cached model instance or None if not loaded
    """
    return _demucs_model


def separate_stems(
    audio_path: str,
    output_dir: str,
    model_name: str = "htdemucs",
    model: Optional[any] = None
) -> Dict[str, str]:
    """
    Separate audio file into stems using Demucs

    Args:
        audio_path: Path to audio file to separate
        output_dir: Directory to save separated stems
        model_name: Demucs model to use (if model is None)
        model: Pre-loaded Demucs model (optional)

    Returns:
        Dictionary mapping stem names to file paths:
        {
            'bass': '/path/to/bass.wav',
            'drums': '/path/to/drums.wav',
            'other': '/path/to/other.wav',
            'vocals': '/path/to/vocals.wav'
        }

    Raises:
        FileNotFoundError: If audio file not found
        RuntimeError: If stem separation fails
    """
    # Ensure Demucs modules are loaded
    _ensure_demucs_modules()

    # Validate audio file exists
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load model if not provided
    if model is None:
        model = _demucs_model
        if model is None:
            logger.info(f"Loading Demucs model on-demand: {model_name}")
            model = load_demucs_model(model_name)

    logger.info(f"🎵 Separating stems: {audio_path}")
    logger.info(f"   Output: {output_dir}")

    try:
        # Load audio
        wav, sr = torchaudio.load(audio_path)

        # Resample to model sample rate if needed
        if sr != model.samplerate:
            logger.info(f"Resampling from {sr}Hz to {model.samplerate}Hz")
            wav = torchaudio.functional.resample(wav, sr, model.samplerate)

        # Ensure stereo (Demucs expects 2 channels)
        if wav.shape[0] == 1:
            wav = wav.repeat(2, 1)
        elif wav.shape[0] > 2:
            wav = wav[:2, :]  # Take first 2 channels

        # Add batch dimension
        wav = wav.unsqueeze(0)

        # Apply model for stem separation
        device = "cuda" if torch.cuda.is_available() else "cpu"
        wav = wav.to(device)

        with torch.no_grad():
            sources = apply_model(
                model,
                wav,
                device=device,
                shifts=1,
                split=True,
                overlap=0.25
            )

        # Demucs htdemucs outputs: [batch, sources, channels, time]
        # sources order: drums, bass, other, vocals
        sources = sources.squeeze(0).cpu()

        # Save each stem
        stem_names = model.sources  # ['drums', 'bass', 'other', 'vocals']
        stem_paths = {}

        for i, stem_name in enumerate(stem_names):
            stem_audio = sources[i]

            # Save stem as WAV file
            stem_filename = f"{stem_name}.wav"
            stem_path = os.path.join(output_dir, stem_filename)

            torchaudio.save(
                stem_path,
                stem_audio,
                model.samplerate,
                encoding="PCM_S",
                bits_per_sample=16
            )

            stem_paths[stem_name] = stem_path
            logger.info(f"   ✅ Saved {stem_name} stem: {stem_path}")

        logger.info(f"✅ Stem separation complete: {len(stem_paths)} stems")
        return stem_paths

    except Exception as e:
        logger.error(f"❌ Stem separation failed: {e}")
        raise RuntimeError(f"Stem separation failed: {e}")


def unload_model():
    """
    Unload Demucs model from memory
    Useful for testing or memory management
    """
    global _demucs_model

    if _demucs_model is not None:
        logger.info("Unloading Demucs model from memory")
        _demucs_model = None

        # Force garbage collection
        import gc
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
