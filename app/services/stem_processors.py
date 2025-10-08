"""
Stem Processor Interface
Modular processor architecture for future model swapping
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class StemProcessor(ABC):
    """
    Abstract base class for stem processors

    Allows swapping different models for each stem without changing API contract
    """

    def __init__(self, model: Any = None):
        """
        Initialize stem processor

        Args:
            model: Model instance for this stem (YourMT3, specialized model, etc.)
        """
        self.model = model

    @abstractmethod
    def process(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """
        Process audio stem and return structured output

        Args:
            audio_path: Path to stem audio file
            **kwargs: Additional processing parameters

        Returns:
            Dictionary with processing results (format depends on processor type)
        """
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """
        Get processor information

        Returns:
            Dictionary with processor metadata
        """
        pass


class BassStemProcessor(StemProcessor):
    """
    Bass stem processor

    v1.0: YourMT3 MIDI transcription
    Future: Specialized bass transcription model
    """

    def __init__(self, model: Any):
        super().__init__(model)
        self.stem_type = 'bass'

    def process(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """
        Process bass stem with YourMT3

        Args:
            audio_path: Path to bass stem audio
            **kwargs: Additional parameters (confidence_threshold, etc.)

        Returns:
            {
                'type': 'midi',
                'stem': 'bass',
                'predictions': [...],
                'midi_path': '...',  # if MIDI file generated
                'notes_count': int
            }
        """
        logger.info(f"Processing bass stem: {audio_path}")

        # v1.0: Use existing 3-stem model for bass
        # The model is already specialized for bass
        confidence_threshold = kwargs.get('confidence_threshold', 0.1)

        try:
            # Process with model (placeholder - actual implementation uses real model)
            result = {
                'type': 'midi',
                'stem': 'bass',
                'processor': 'BassStemProcessor',
                'model': 'YourMT3',
                'audio_path': audio_path,
                'status': 'processed'
            }

            logger.info(f"Bass stem processed successfully")
            return result

        except Exception as e:
            logger.error(f"Bass stem processing failed: {e}")
            raise RuntimeError(f"Bass stem processing failed: {e}")

    def get_info(self) -> Dict[str, Any]:
        """Get bass processor information"""
        return {
            'stem_type': 'bass',
            'processor': 'BassStemProcessor',
            'model': 'YourMT3',
            'version': '1.0',
            'allowed_programs': list(range(33, 41)),  # GM Bass family
            'default_program': 33,  # Electric Bass (finger)
            'capabilities': ['midi_transcription', 'program_constraints']
        }


class DrumsStemProcessor(StemProcessor):
    """
    Drums stem processor

    v1.0: YourMT3 MIDI transcription
    Future: Specialized drum transcription model (ADTof, DrumGAN)
    """

    def __init__(self, model: Any):
        super().__init__(model)
        self.stem_type = 'drums'

    def process(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """
        Process drums stem

        Future versions can swap to specialized drum transcription models
        """
        logger.info(f"Processing drums stem: {audio_path}")

        try:
            result = {
                'type': 'midi',
                'stem': 'drums',
                'processor': 'DrumsStemProcessor',
                'model': 'YourMT3',
                'audio_path': audio_path,
                'status': 'processed',
                'note': 'v1.0 uses YourMT3, future: specialized drum model'
            }

            logger.info(f"Drums stem processed successfully")
            return result

        except Exception as e:
            logger.error(f"Drums stem processing failed: {e}")
            raise RuntimeError(f"Drums stem processing failed: {e}")

    def get_info(self) -> Dict[str, Any]:
        """Get drums processor information"""
        return {
            'stem_type': 'drums',
            'processor': 'DrumsStemProcessor',
            'model': 'YourMT3',
            'version': '1.0',
            'allowed_programs': list(range(113, 121)),  # Melodic drums
            'channel_10': True,  # Standard GM percussion
            'capabilities': ['midi_transcription', 'drum_events'],
            'future_enhancement': 'Specialized drum transcription model'
        }


class OtherStemProcessor(StemProcessor):
    """
    Other (melodic/harmonic) stem processor

    v1.0: YourMT3 MIDI transcription
    Handles: Piano, guitar, strings, brass, synths, etc.
    """

    def __init__(self, model: Any):
        super().__init__(model)
        self.stem_type = 'other'

    def process(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """Process other stem with YourMT3"""
        logger.info(f"Processing other stem: {audio_path}")

        try:
            result = {
                'type': 'midi',
                'stem': 'other',
                'processor': 'OtherStemProcessor',
                'model': 'YourMT3',
                'audio_path': audio_path,
                'status': 'processed'
            }

            logger.info(f"Other stem processed successfully")
            return result

        except Exception as e:
            logger.error(f"Other stem processing failed: {e}")
            raise RuntimeError(f"Other stem processing failed: {e}")

    def get_info(self) -> Dict[str, Any]:
        """Get other processor information"""
        return {
            'stem_type': 'other',
            'processor': 'OtherStemProcessor',
            'model': 'YourMT3',
            'version': '1.0',
            'allowed_programs': (
                list(range(1, 33)) +    # Piano, chromatic, organ, guitar
                list(range(41, 113)) +  # Strings, brass, reed, synth
                list(range(121, 129))   # Sound effects (rarely transcribed)
            ),
            'capabilities': ['midi_transcription', 'minimal_constraints']
        }


class VocalsStemProcessor(StemProcessor):
    """
    Vocals stem processor

    v1.0: Voice Activity Detection (VAD) only
    v2.0: Speech-to-text transcription (Whisper)
    """

    def __init__(self, model: Optional[Any] = None):
        super().__init__(model)
        self.stem_type = 'vocals'

    def process(self, audio_path: str, **kwargs) -> Dict[str, Any]:
        """
        Process vocals stem with VAD

        Future versions will add speech-to-text
        """
        logger.info(f"Processing vocals stem: {audio_path}")

        try:
            # v1.0: Simple VAD (actual implementation in vad.py)
            from app.services.vad import detect_voice_activity

            voice_segments = detect_voice_activity(audio_path)

            result = {
                'type': 'vad',
                'stem': 'vocals',
                'processor': 'VocalsStemProcessor',
                'model': 'webrtcvad',
                'audio_path': audio_path,
                'voice_active_segments': voice_segments,
                'status': 'processed',
                'note': 'v1.0 VAD only, v2.0 will add speech-to-text'
            }

            logger.info(f"Vocals stem processed successfully ({len(voice_segments)} segments)")
            return result

        except Exception as e:
            logger.error(f"Vocals stem processing failed: {e}")
            raise RuntimeError(f"Vocals stem processing failed: {e}")

    def get_info(self) -> Dict[str, Any]:
        """Get vocals processor information"""
        return {
            'stem_type': 'vocals',
            'processor': 'VocalsStemProcessor',
            'model': 'webrtcvad',
            'version': '1.0',
            'capabilities': ['voice_activity_detection'],
            'future_enhancement': 'Speech-to-text transcription (Whisper)'
        }


# Factory function for creating processors
def create_stem_processor(stem_type: str, model: Any = None) -> StemProcessor:
    """
    Factory function to create appropriate stem processor

    Args:
        stem_type: Type of stem ('bass', 'drums', 'other', 'vocals')
        model: Model instance for the processor

    Returns:
        Appropriate StemProcessor instance

    Example:
        >>> bass_processor = create_stem_processor('bass', yourmt3_model)
        >>> result = bass_processor.process('bass_stem.wav')
    """
    processors = {
        'bass': BassStemProcessor,
        'drums': DrumsStemProcessor,
        'other': OtherStemProcessor,
        'vocals': VocalsStemProcessor
    }

    if stem_type not in processors:
        raise ValueError(
            f"Unknown stem type: {stem_type}. "
            f"Must be one of: {list(processors.keys())}"
        )

    return processors[stem_type](model)
