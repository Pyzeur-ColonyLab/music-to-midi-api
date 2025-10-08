"""
Model Download Script
Downloads pre-trained models for Music-to-MIDI API
"""

import os
import sys
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def download_demucs_models():
    """
    Download Demucs models for stem separation

    Demucs models are downloaded on first use by the library
    """
    try:
        from demucs.pretrained import get_model

        logger.info("Downloading Demucs htdemucs model...")
        model = get_model('htdemucs')
        logger.info("✅ Demucs model ready")
        return True

    except Exception as e:
        logger.error(f"Failed to download Demucs model: {e}")
        return False


def check_yourmt3_models():
    """
    Check if YourMT3 3-stem models exist

    These models should be pre-trained and placed in app/models/3_stems_models/
    """
    models_dir = Path("app/models/3_stems_models")

    required_files = [
        'bass_metadata.json',
        'drums_metadata.json',
        'other_metadata.json'
    ]

    logger.info("Checking for YourMT3 3-stem models...")

    if not models_dir.exists():
        logger.warning(f"❌ Models directory not found: {models_dir}")
        logger.warning("   Please ensure 3-stem models are placed in this directory")
        return False

    missing_files = []
    for file in required_files:
        if not (models_dir / file).exists():
            missing_files.append(file)

    if missing_files:
        logger.warning(f"❌ Missing model files: {', '.join(missing_files)}")
        logger.warning(f"   Expected in: {models_dir}")
        return False

    logger.info("✅ YourMT3 models found")
    return True


def main():
    """Download and verify all required models"""
    logger.info("="*60)
    logger.info("🤖 Music-to-MIDI API - Model Setup")
    logger.info("="*60)

    success = True

    # Download Demucs models
    logger.info("\n1. Demucs Models (Stem Separation)")
    if not download_demucs_models():
        success = False

    # Check YourMT3 models
    logger.info("\n2. YourMT3 Models (3-Stem Classifiers)")
    if not check_yourmt3_models():
        success = False
        logger.warning("\n⚠️  YourMT3 models not found!")
        logger.warning("   These must be manually placed in app/models/3_stems_models/")
        logger.warning("   Required files:")
        logger.warning("   - bass_metadata.json + bass model file (.pth)")
        logger.warning("   - drums_metadata.json + drums model file (.pth)")
        logger.warning("   - other_metadata.json + other model file (.pth)")

    logger.info("\n" + "="*60)
    if success:
        logger.info("✅ Model setup complete!")
    else:
        logger.warning("⚠️  Some models need manual setup")
        logger.info("\nThe API will start but may not function until all models are available.")

    logger.info("="*60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
