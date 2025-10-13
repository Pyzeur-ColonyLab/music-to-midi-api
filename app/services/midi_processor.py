"""
MIDI Processing Service
MIDI analysis and JSON conversion
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


def analyze_midi(midi_path: str) -> Dict[str, Any]:
    """
    Analyze MIDI file and extract structured metadata

    Args:
        midi_path: Path to MIDI file

    Returns:
        Dictionary with MIDI analysis:
            - instruments: List of instruments with program numbers
            - total_notes: Total number of notes
            - duration: Duration in seconds
            - tracks: Number of tracks

    Raises:
        FileNotFoundError: If MIDI file not found
        RuntimeError: If MIDI analysis fails

    Example:
        >>> analysis = analyze_midi("output.mid")
        >>> print(f"Total notes: {analysis['total_notes']}")
    """
    midi_file = Path(midi_path)
    if not midi_file.exists():
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")

    try:
        import pretty_midi

        # Load MIDI file
        midi = pretty_midi.PrettyMIDI(str(midi_file))

        # Extract instruments
        instruments = []
        total_notes = 0

        for idx, instrument in enumerate(midi.instruments):
            notes_count = len(instrument.notes)
            total_notes += notes_count

            instruments.append({
                'index': idx,
                'program': instrument.program,
                'name': pretty_midi.program_to_instrument_name(instrument.program),
                'notes': notes_count,
                'is_drum': instrument.is_drum
            })

        analysis = {
            'instruments': instruments,
            'total_notes': total_notes,
            'duration': midi.get_end_time(),
            'tracks': len(midi.instruments)
        }

        logger.info(f"MIDI analysis: {total_notes} notes, {len(instruments)} instruments")
        return analysis

    except Exception as e:
        logger.error(f"MIDI analysis failed: {e}")
        raise RuntimeError(f"MIDI analysis failed: {e}")


def midi_to_json(midi_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert MIDI file to JSON representation

    Args:
        midi_path: Path to MIDI file
        output_path: Optional path to save JSON file

    Returns:
        Dictionary with complete MIDI data in JSON format

    Example:
        >>> json_data = midi_to_json("output.mid", "output.json")
        >>> print(json.dumps(json_data, indent=2))
    """
    try:
        import pretty_midi

        midi_file = Path(midi_path)
        if not midi_file.exists():
            raise FileNotFoundError(f"MIDI file not found: {midi_path}")

        # Load MIDI file
        midi = pretty_midi.PrettyMIDI(str(midi_file))

        # Build JSON structure
        json_data = {
            'metadata': {
                'duration': midi.get_end_time(),
                'total_tracks': len(midi.instruments),
                'file_path': str(midi_file)
            },
            'instruments': [],
            'tempo_changes': [
                {
                    'time': float(time),
                    'tempo': float(tempo)
                }
                for time, tempo in midi.get_tempo_changes()
            ]
        }

        # Extract instruments and notes
        for idx, instrument in enumerate(midi.instruments):
            instrument_data = {
                'index': idx,
                'program': instrument.program,
                'name': pretty_midi.program_to_instrument_name(instrument.program),
                'is_drum': instrument.is_drum,
                'notes': [
                    {
                        'pitch': note.pitch,
                        'start': float(note.start),
                        'end': float(note.end),
                        'velocity': note.velocity
                    }
                    for note in instrument.notes
                ]
            }
            json_data['instruments'].append(instrument_data)

        # Save to file if output path provided
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w') as f:
                json.dump(json_data, f, indent=2)

            logger.info(f"JSON saved to: {output_path}")

        return json_data

    except Exception as e:
        logger.error(f"MIDI to JSON conversion failed: {e}")
        raise RuntimeError(f"MIDI to JSON conversion failed: {e}")


def create_midi_from_notes(
    notes_data: List[Dict[str, Any]],
    output_path: str,
    program: int = 0,
    tempo: int = 120
) -> str:
    """
    Create MIDI file from note data

    Args:
        notes_data: List of notes with pitch, start, end, velocity
        output_path: Path to save MIDI file
        program: MIDI program number (0-127)
        tempo: Tempo in BPM

    Returns:
        Path to created MIDI file

    Example:
        >>> notes = [
        ...     {'pitch': 60, 'start': 0.0, 'end': 1.0, 'velocity': 100},
        ...     {'pitch': 64, 'start': 1.0, 'end': 2.0, 'velocity': 100}
        ... ]
        >>> midi_path = create_midi_from_notes(notes, "output.mid", program=33)
    """
    try:
        import pretty_midi

        # Create MIDI object
        midi = pretty_midi.PrettyMIDI(initial_tempo=tempo)

        # Create instrument
        instrument = pretty_midi.Instrument(program=program)

        # Add notes
        for note_data in notes_data:
            note = pretty_midi.Note(
                velocity=note_data.get('velocity', 100),
                pitch=note_data['pitch'],
                start=note_data['start'],
                end=note_data['end']
            )
            instrument.notes.append(note)

        # Add instrument to MIDI
        midi.instruments.append(instrument)

        # Save MIDI file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        midi.write(str(output_file))

        logger.info(f"MIDI file created: {output_path}")
        return str(output_file)

    except Exception as e:
        logger.error(f"MIDI creation failed: {e}")
        raise RuntimeError(f"MIDI creation failed: {e}")


# ============================================================================
# GENERAL MIDI LEVEL 1 SPECIFICATION COMPLIANCE
# Based on: RP-003_General_MIDI_System_Level_1_Specification_96-1-4_0.1.pdf
# ============================================================================

class GMInstrumentCategories:
    """
    General MIDI Level 1 Instrument Categories (Official Specification)

    Programs are 0-indexed here (0-127), while GM spec uses 1-indexed (1-128)
    Channel 10 (index 9) is reserved for percussion/drums
    """

    # Melodic Instrument Groups (Table 1 & 2 from GM spec)
    PIANO = list(range(0, 8))  # 1-8: Acoustic Grand -> Clavi
    CHROMATIC_PERCUSSION = list(range(8, 16))  # 9-16: Celesta -> Dulcimer
    ORGAN = list(range(16, 24))  # 17-24: Drawbar Organ -> Tango Accordion
    GUITAR = list(range(24, 32))  # 25-32: Acoustic Guitar (nylon) -> Guitar harmonics
    BASS = list(range(32, 40))  # 33-40: Acoustic Bass -> Synth Bass 2
    STRINGS = list(range(40, 48))  # 41-48: Violin -> Timpani
    ENSEMBLE = list(range(48, 56))  # 49-56: String Ensemble 1 -> Orchestra Hit
    BRASS = list(range(56, 64))  # 57-64: Trumpet -> SynthBrass 2
    REED = list(range(64, 72))  # 65-72: Soprano Sax -> Clarinet
    PIPE = list(range(72, 80))  # 73-80: Piccolo -> Ocarina
    SYNTH_LEAD = list(range(80, 88))  # 81-88: Lead 1 (square) -> Lead 8 (bass + lead)
    SYNTH_PAD = list(range(88, 96))  # 89-96: Pad 1 (new age) -> Pad 8 (sweep)
    SYNTH_EFFECTS = list(range(96, 104))  # 97-104: FX 1 (rain) -> FX 8 (sci-fi)
    ETHNIC = list(range(104, 112))  # 105-112: Sitar -> Shanai
    PERCUSSIVE = list(range(112, 120))  # 113-120: Tinkle Bell -> Reverse Cymbal
    SOUND_EFFECTS = list(range(120, 128))  # 121-128: Guitar Fret Noise -> Gunshot

    # Percussion: Channel 10 only, MIDI Keys 35-81 (Table 3 from GM spec)
    DRUM_KEYS = list(range(35, 82))  # Bass Drum -> Open Triangle

    # Voice-like instruments
    VOICE_INSTRUMENTS = [52, 53, 54]  # Choir Aahs, Voice Oohs, Synth Voice (programs 53-55 in spec)


class StemInstrumentMapper:
    """
    Maps stem types to allowed General MIDI instruments per GM Level 1 specification

    Ensures:
    - Drums stem: Only percussion on Channel 10
    - Bass stem: Only bass instruments + low-frequency instruments
    - Other stem: Melodic instruments excluding bass and vocals
    - Vocals stem: Voice and breath-based instruments
    """

    @staticmethod
    def get_allowed_programs(stem_type: str) -> set:
        """
        Get allowed GM program numbers for a stem type per GM Level 1 spec

        Args:
            stem_type: One of 'drums', 'bass', 'other', 'vocals'

        Returns:
            Set of allowed program numbers (0-127)
        """
        stem_type = stem_type.lower()

        if stem_type == 'drums':
            # Drums: Only GM Percussion (Channel 10)
            # Return percussive melodic instruments as fallback
            return set(GMInstrumentCategories.PERCUSSIVE)

        elif stem_type == 'bass':
            # Bass: GM Bass family (33-40) + low-frequency instruments
            allowed = set(GMInstrumentCategories.BASS)
            allowed.add(43)  # Contrabass (program 44 in spec)
            allowed.add(58)  # Tuba (program 59 in spec)
            return allowed

        elif stem_type == 'vocals':
            # Vocals: Voice instruments + breath-based (brass, reed, pipe)
            allowed = set(GMInstrumentCategories.VOICE_INSTRUMENTS)
            allowed.update(GMInstrumentCategories.BRASS)  # Trumpet, Trombone, etc.
            allowed.update(GMInstrumentCategories.REED)  # Sax, Oboe, Clarinet, etc.
            allowed.update(GMInstrumentCategories.PIPE)  # Flute, Piccolo, etc.
            return allowed

        elif stem_type == 'other':
            # Other: All melodic EXCEPT bass, drums, vocals
            allowed = set()
            allowed.update(GMInstrumentCategories.PIANO)
            allowed.update(GMInstrumentCategories.CHROMATIC_PERCUSSION)
            allowed.update(GMInstrumentCategories.ORGAN)
            allowed.update(GMInstrumentCategories.GUITAR)
            allowed.update(GMInstrumentCategories.STRINGS)
            allowed.update(GMInstrumentCategories.ENSEMBLE)
            allowed.update(GMInstrumentCategories.SYNTH_LEAD)
            allowed.update(GMInstrumentCategories.SYNTH_PAD)
            allowed.update(GMInstrumentCategories.SYNTH_EFFECTS)
            allowed.update(GMInstrumentCategories.ETHNIC)
            # Exclude bass-specific instruments
            allowed.discard(43)  # Contrabass
            allowed.discard(58)  # Tuba
            return allowed

        else:
            logger.warning(f"Unknown stem type '{stem_type}', allowing all programs")
            return set(range(0, 128))

    @staticmethod
    def get_default_program(stem_type: str) -> int:
        """
        Get default GM program for a stem type

        Args:
            stem_type: One of 'drums', 'bass', 'other', 'vocals'

        Returns:
            Default program number (0-127)
        """
        defaults = {
            'drums': 118,  # Synth Drum (program 119 in spec)
            'bass': 33,  # Electric Bass (finger) (program 34 in spec)
            'vocals': 52,  # Choir Aahs (program 53 in spec)
            'other': 0,  # Acoustic Grand Piano (program 1 in spec)
        }
        return defaults.get(stem_type.lower(), 0)


def apply_stem_constraints(program: int, stem_type: str) -> int:
    """
    Apply GM Level 1 MIDI program constraints based on stem type

    Enforces General MIDI specification to ensure:
    - Drums stem contains only percussion sounds
    - Bass stem contains only bass instruments
    - Vocals stem contains only voice/breath instruments
    - Other stem contains melodic instruments

    Args:
        program: Original MIDI program number (0-127)
        stem_type: Stem type ('bass', 'drums', 'other', 'vocals')

    Returns:
        Corrected MIDI program number compliant with GM Level 1

    Example:
        >>> # Piano (0) on bass stem -> Electric Bass (33)
        >>> corrected = apply_stem_constraints(0, 'bass')
        >>> assert corrected == 33

        >>> # Violin (40) on drums stem -> Synth Drum (118)
        >>> corrected = apply_stem_constraints(40, 'drums')
        >>> assert corrected == 118
    """
    allowed = StemInstrumentMapper.get_allowed_programs(stem_type)

    if program not in allowed:
        default = StemInstrumentMapper.get_default_program(stem_type)
        logger.info(
            f"GM compliance: program {program} not allowed for {stem_type} stem, "
            f"correcting to {default}"
        )
        return default

    return program


def process_midi_for_stem_compliance(midi_path: str, stem_type: str) -> str:
    """
    Process MIDI file to enforce GM Level 1 compliance for a stem type

    Applies General MIDI specification constraints:
    - Remaps instruments to allowed programs
    - For drums: moves notes to Channel 10 (percussion)
    - For bass: filters to low notes only
    - Ensures no cross-contamination between stem types

    Args:
        midi_path: Path to MIDI file to process
        stem_type: Stem type ('drums', 'bass', 'other', 'vocals')

    Returns:
        Path to processed MIDI file (overwrites original)

    Raises:
        FileNotFoundError: If MIDI file doesn't exist
        RuntimeError: If processing fails
    """
    try:
        import pretty_midi

        midi_file = Path(midi_path)
        if not midi_file.exists():
            raise FileNotFoundError(f"MIDI file not found: {midi_path}")

        logger.info(f"Applying GM Level 1 constraints for {stem_type} stem: {midi_path}")

        # Load MIDI
        midi = pretty_midi.PrettyMIDI(str(midi_file))

        if stem_type.lower() == 'drums':
            # Special handling: Move everything to Channel 10 (GM percussion)
            midi = _process_drums_to_channel_10(midi)
        else:
            # Process melodic instruments
            midi = _process_melodic_instruments(midi, stem_type)

        # Save processed MIDI
        midi.write(str(midi_file))
        logger.info(f"✅ GM compliance applied: {midi_file}")

        return str(midi_file)

    except Exception as e:
        logger.error(f"Failed to process MIDI for GM compliance: {e}")
        raise RuntimeError(f"MIDI processing failed: {e}")


def _process_drums_to_channel_10(midi: 'pretty_midi.PrettyMIDI') -> 'pretty_midi.PrettyMIDI':
    """Move all notes to Channel 10 (percussion) per GM specification"""
    import pretty_midi

    new_midi = pretty_midi.PrettyMIDI()
    percussion = pretty_midi.Instrument(program=0, is_drum=True, name='GM Drums')

    # Collect all notes
    all_notes = []
    for instrument in midi.instruments:
        all_notes.extend(instrument.notes)

    # Remap to GM percussion key range (35-81)
    for note in all_notes:
        if note.pitch < 35:
            note.pitch = 35 + (note.pitch % 2)  # Bass drum range
        elif note.pitch > 81:
            note.pitch = 79 + (note.pitch % 3)  # High percussion range
        percussion.notes.append(note)

    new_midi.instruments.append(percussion)
    logger.info(f"Drums: moved {len(all_notes)} notes to Channel 10 (GM percussion)")

    return new_midi


def _process_melodic_instruments(midi: 'pretty_midi.PrettyMIDI', stem_type: str) -> 'pretty_midi.PrettyMIDI':
    """Apply GM program constraints to melodic instruments"""
    allowed_programs = StemInstrumentMapper.get_allowed_programs(stem_type)
    default_program = StemInstrumentMapper.get_default_program(stem_type)

    for instrument in midi.instruments:
        if instrument.is_drum:
            # Remove drums from melodic stems
            instrument.notes = []
            continue

        # Remap program if not allowed
        if instrument.program not in allowed_programs:
            logger.debug(f"Remapping program {instrument.program} -> {default_program} for {stem_type}")
            instrument.program = default_program

        # Bass-specific filtering: keep only low notes
        if stem_type.lower() == 'bass':
            original_count = len(instrument.notes)
            instrument.notes = [n for n in instrument.notes if n.pitch < 65]  # Below F4
            if original_count != len(instrument.notes):
                logger.debug(f"Bass filter: kept {len(instrument.notes)}/{original_count} low notes")

    return midi
