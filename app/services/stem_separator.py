"""
Stem Separation Service
Demucs-based audio source separation
"""

import logging
from typing import Dict, Optional
from pathlib import Path
import os

logger = logging.getLogger(__name__)


def separate_stems(
    audio_path: str,
    output_dir: Optional[str] = None,
    model: str = "htdemucs"
) -> Dict[str, str]:
    """
    Separate audio into 4 stems using Demucs

    Stems:
        - bass: Bass instruments
        - drums: Drums and percussion
        - other: Other melodic/harmonic instruments
        - vocals: Vocal tracks

    Args:
        audio_path: Path to input audio file
        output_dir: Directory for separated stems (default: stems/ next to audio)
        model: Demucs model to use (htdemucs, mdx, mdx_extra, etc.)

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

    Example:
        >>> stems = separate_stems("song.mp3")
        >>> print(f"Bass stem: {stems['bass']}")
    """
    try:
        import torch
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        import torchaudio

        # Validate input file
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Setup output directory
        if output_dir is None:
            output_dir = audio_file.parent / "stems" / audio_file.stem
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting stem separation for: {audio_file.name}")
        logger.info(f"Using Demucs model: {model}")
        logger.info(f"Output directory: {output_dir}")

        # Load Demucs model
        demucs_model = get_model(model)
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        demucs_model.to(device)

        logger.info(f"Demucs loaded on device: {device}")

        # Load audio
        waveform, sample_rate = torchaudio.load(str(audio_file))

        # Ensure stereo
        if waveform.shape[0] == 1:
            waveform = waveform.repeat(2, 1)

        # Move to device
        waveform = waveform.to(device)

        # Apply separation
        logger.info("Running stem separation...")
        with torch.no_grad():
            sources = apply_model(
                demucs_model,
                waveform[None],
                device=device,
                progress=True
            )[0]

        # Demucs output order: drums, bass, other, vocals
        stem_names = ['drums', 'bass', 'other', 'vocals']
        stem_paths = {}

        # Save each stem
        for idx, stem_name in enumerate(stem_names):
            stem_audio = sources[idx].cpu()
            stem_path = output_dir / f"{stem_name}.wav"

            torchaudio.save(
                str(stem_path),
                stem_audio,
                sample_rate
            )

            stem_paths[stem_name] = str(stem_path)
            logger.info(f"  ✓ {stem_name}: {stem_path.name}")

        logger.info(f"✅ Stem separation completed: {len(stem_paths)} stems")
        return stem_paths

    except ImportError as e:
        logger.error(f"Demucs not installed: {e}")
        raise RuntimeError(
            "Demucs not available. Install with: pip install demucs"
        )
    except Exception as e:
        logger.error(f"Stem separation failed: {e}")
        raise RuntimeError(f"Stem separation failed: {e}")


def cleanup_stems(stem_paths: Dict[str, str]):
    """
    Remove stem files from disk

    Args:
        stem_paths: Dictionary of stem paths from separate_stems()

    Example:
        >>> stems = separate_stems("song.mp3")
        >>> # ... process stems ...
        >>> cleanup_stems(stems)
    """
    for stem_name, stem_path in stem_paths.items():
        try:
            if os.path.exists(stem_path):
                os.remove(stem_path)
                logger.info(f"Removed stem file: {stem_name}")
        except Exception as e:
            logger.warning(f"Failed to remove {stem_name} stem: {e}")

    # Try to remove parent directory if empty
    try:
        if stem_paths:
            first_path = Path(list(stem_paths.values())[0])
            parent_dir = first_path.parent

            if parent_dir.exists() and not list(parent_dir.iterdir()):
                parent_dir.rmdir()
                logger.info(f"Removed empty directory: {parent_dir}")
    except Exception as e:
        logger.warning(f"Failed to cleanup directory: {e}")


def get_available_models() -> list:
    """
    Get list of available Demucs models

    Returns:
        List of model names

    Example:
        >>> models = get_available_models()
        >>> print(f"Available models: {models}")
    """
    try:
        from demucs.pretrained import PRETRAINED_MODELS
        return list(PRETRAINED_MODELS.keys())
    except ImportError:
        logger.warning("Demucs not installed")
        return []
