"""
MR-MT3 Service Wrapper
Integrates MR-MT3 (Memory Retaining Multi-Track Music Transcription) model
"""

import os
import sys
import torch
import librosa
import numpy as np
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MRMT3Service:
    """
    Service wrapper for MR-MT3 model integration

    Features:
    - Memory retention mechanism for better instrument separation
    - Multi-track MIDI generation
    - Reduced instrument leakage
    """

    def __init__(
        self,
        model_path: str = "./models/mr-mt3/mt3.pth",
        config_path: str = "./models/mr-mt3/config.json",
        device: Optional[str] = None
    ):
        """
        Initialize MR-MT3 service

        Args:
            model_path: Path to MR-MT3 model checkpoint
            config_path: Path to model configuration
            device: 'cuda' or 'cpu' (auto-detected if None)
        """
        self.model_path = os.path.abspath(model_path)
        self.config_path = os.path.abspath(config_path)

        # Auto-detect device
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        logger.info(f"🔧 Initializing MR-MT3 Service on device: {self.device}")

        # Add MR-MT3 repository to path
        mr_mt3_dir = os.path.dirname(self.model_path)
        mr_mt3_repo = os.path.join(mr_mt3_dir, "MR-MT3")
        if os.path.exists(mr_mt3_repo):
            sys.path.insert(0, mr_mt3_repo)

        self.model_loaded = False
        self.handler = None

    def load_model(self):
        """Load MR-MT3 model"""
        try:
            from inference import InferenceHandler

            logger.info(f"📥 Loading MR-MT3 model from {self.model_path}")

            if not os.path.exists(self.model_path):
                raise FileNotFoundError(
                    f"Model checkpoint not found at {self.model_path}. "
                    f"Please run setup script to download the model."
                )

            # Initialize handler
            # Note: InferenceHandler expects config at models/mr-mt3/MR-MT3/config/mt3_config.json
            self.handler = InferenceHandler(
                weight_path=self.model_path,
                device=self.device
            )

            self.model_loaded = True
            logger.info("✅ MR-MT3 model loaded successfully!")

        except Exception as e:
            logger.error(f"❌ Failed to load MR-MT3 model: {e}")
            raise

    def transcribe_audio(
        self,
        audio_path: str,
        output_path: str,
        target_sr: int = 16000
    ) -> str:
        """
        Transcribe audio file to MIDI

        Args:
            audio_path: Path to input audio file
            output_path: Path for output MIDI file
            target_sr: Target sample rate (16kHz for MR-MT3)

        Returns:
            Path to generated MIDI file
        """
        if not self.model_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        logger.info(f"🎵 Transcribing: {audio_path}")

        try:
            # Load and preprocess audio
            logger.debug(f"Loading audio at {target_sr}Hz mono...")
            audio, sr = librosa.load(audio_path, sr=target_sr, mono=True)

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Run inference
            logger.debug(f"Running MR-MT3 inference...")
            self.handler.inference(audio, audio_path, outpath=output_path)

            # Verify output
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"MIDI file was not created at {output_path}")

            logger.info(f"✅ Transcription complete: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ Transcription failed: {e}")
            raise

    def transcribe_audio_data(
        self,
        audio_data: np.ndarray,
        output_path: str,
        sample_rate: int = 16000
    ) -> str:
        """
        Transcribe audio numpy array to MIDI

        Args:
            audio_data: Audio data as numpy array
            output_path: Path for output MIDI file
            sample_rate: Sample rate of audio data

        Returns:
            Path to generated MIDI file
        """
        if not self.model_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        try:
            # Ensure mono
            if len(audio_data.shape) > 1:
                audio_data = librosa.to_mono(audio_data)

            # Resample if needed
            if sample_rate != 16000:
                audio_data = librosa.resample(
                    audio_data,
                    orig_sr=sample_rate,
                    target_sr=16000
                )

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Run inference
            # Note: InferenceHandler requires audio_path, use output_path as placeholder
            self.handler.inference(audio_data, output_path, outpath=output_path)

            if not os.path.exists(output_path):
                raise FileNotFoundError(f"MIDI file was not created at {output_path}")

            logger.info(f"✅ Transcription complete: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ Transcription from audio data failed: {e}")
            raise

    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model_name": "MR-MT3",
            "full_name": "Memory Retaining Multi-Track Music Transcription",
            "version": "1.0",
            "device": self.device,
            "model_loaded": self.model_loaded,
            "checkpoint_path": self.model_path,
            "features": [
                "Memory retention mechanism",
                "Multi-track MIDI generation",
                "Instrument leakage mitigation",
                "T5-based architecture"
            ],
            "paper": "https://arxiv.org/abs/2403.10024",
            "github": "https://github.com/gudgud96/MR-MT3"
        }

    def cleanup(self):
        """Cleanup model resources"""
        if self.handler is not None:
            del self.handler
            self.handler = None
            self.model_loaded = False

            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            logger.info("🧹 MR-MT3 model resources cleaned up")


# Global instance
_mr_mt3_instance: Optional[MRMT3Service] = None


def get_mr_mt3_service(
    model_path: str = "./models/mr-mt3/mt3.pth",
    config_path: str = "./models/mr-mt3/config.json"
) -> MRMT3Service:
    """
    Get or create global MR-MT3 service instance

    Args:
        model_path: Path to model checkpoint
        config_path: Path to configuration

    Returns:
        MRMT3Service instance
    """
    global _mr_mt3_instance

    if _mr_mt3_instance is None:
        _mr_mt3_instance = MRMT3Service(
            model_path=model_path,
            config_path=config_path
        )
        _mr_mt3_instance.load_model()

    return _mr_mt3_instance
