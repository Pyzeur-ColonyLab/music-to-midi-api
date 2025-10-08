"""
Model Loading Service
Handles YourMT3 and stem-specific model initialization
"""

import torch
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from app.models.stem_integrated_classifier import StemIntegratedClassifier

logger = logging.getLogger(__name__)

# Global model instance (singleton pattern for efficiency)
_model_instance: Optional[StemIntegratedClassifier] = None


def load_yourmt3_model(
    models_dir: str = "app/models/3_stems_models",
    device: Optional[str] = None,
    sample_rate: int = 22050,
    segment_duration: float = 4.0
) -> StemIntegratedClassifier:
    """
    Load YourMT3 model with 3-stem specialized classifiers

    Args:
        models_dir: Path to models directory containing stem-specific models
        device: Device to use ('cuda', 'cpu', or None for auto-detect)
        sample_rate: Audio sample rate for processing
        segment_duration: Duration of audio segments in seconds

    Returns:
        StemIntegratedClassifier instance ready for inference

    Raises:
        FileNotFoundError: If model files not found
        RuntimeError: If model initialization fails
    """
    global _model_instance

    # Auto-detect device if not specified
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Auto-detected device: {device}")

    # Validate models directory exists
    models_path = Path(models_dir)
    if not models_path.exists():
        raise FileNotFoundError(
            f"Models directory not found: {models_dir}\n"
            f"Please ensure 3-stem models are available at this location"
        )

    logger.info(f"🚀 Loading YourMT3 with 3-stem specialized models...")
    logger.info(f"   Models directory: {models_dir}")
    logger.info(f"   Device: {device}")
    logger.info(f"   Sample rate: {sample_rate}Hz")
    logger.info(f"   Segment duration: {segment_duration}s")

    try:
        # Initialize stem-integrated classifier
        model = StemIntegratedClassifier(
            models_dir=models_dir,
            device=device,
            sample_rate=sample_rate,
            segment_duration=segment_duration
        )

        # Cache instance for reuse
        _model_instance = model

        logger.info("✅ YourMT3 model loaded successfully")
        return model

    except Exception as e:
        logger.error(f"❌ Failed to load YourMT3 model: {e}")
        raise RuntimeError(f"Model loading failed: {e}")


def get_model_instance() -> Optional[StemIntegratedClassifier]:
    """
    Get cached model instance

    Returns:
        Cached model instance or None if not loaded
    """
    return _model_instance


def get_model_info() -> Dict[str, Any]:
    """
    Get information about loaded model

    Returns:
        Dictionary with model metadata

    Raises:
        RuntimeError: If model not loaded
    """
    if _model_instance is None:
        raise RuntimeError("Model not loaded. Call load_yourmt3_model() first.")

    # Get model info from integrated classifier
    model_info = {
        'system_type': '3-Stem Specialized Models',
        'device': str(_model_instance.device),
        'sample_rate': _model_instance.sample_rate,
        'segment_duration': _model_instance.segment_duration,
        'models': {
            'bass': {
                'classes': 8,
                'accuracy': 0.99,
                'description': 'Bass-specific instrument classifier'
            },
            'drums': {
                'classes': 8,
                'accuracy': 0.98,
                'description': 'Drums-specific instrument classifier'
            },
            'other': {
                'classes': 8,
                'accuracy': 0.84,
                'description': 'Other instruments classifier'
            }
        },
        'total_classes': 24,
        'audio_processing': {
            'sample_rate': _model_instance.sample_rate,
            'segment_duration': _model_instance.segment_duration,
            'beat_detection': True,
            'stem_separation': True
        }
    }

    return model_info


def unload_model():
    """
    Unload model from memory
    Useful for testing or memory management
    """
    global _model_instance

    if _model_instance is not None:
        logger.info("Unloading model from memory")
        _model_instance = None

        # Force garbage collection
        import gc
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
