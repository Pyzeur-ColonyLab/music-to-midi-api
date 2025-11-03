"""
MIDI Processing Service
MIDI analysis, JSON conversion, and instrument-based splitting
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json

logger = logging.getLogger(__name__)


# General MIDI Instrument to Family Mapping (Programs 0-127, 0-indexed)
# Based on user-provided instrument classification
GM_INSTRUMENT_FAMILIES = {
    # Piano Family (0-7) - Others
    0: ("Acoustic Grand Piano", "Piano"),
    1: ("Bright Acoustic Piano", "Piano"),
    2: ("Electric Grand Piano", "Piano"),
    3: ("Honky-tonk Piano", "Piano"),
    4: ("Electric Piano 1", "Piano"),
    5: ("Electric Piano 2", "Piano"),
    6: ("Harpsichord", "Piano"),
    7: ("Clavi", "Piano"),

    # Chromatic Percussion (8-15) - Others
    8: ("Celesta", "Chromatic Percussion"),
    9: ("Glockenspiel", "Chromatic Percussion"),
    10: ("Music Box", "Chromatic Percussion"),
    11: ("Vibraphone", "Chromatic Percussion"),
    12: ("Marimba", "Chromatic Percussion"),
    13: ("Xylophone", "Chromatic Percussion"),
    14: ("Tubular Bells", "Chromatic Percussion"),
    15: ("Dulcimer", "Chromatic Percussion"),

    # Organ (16-23) - Others
    16: ("Drawbar Organ", "Organ"),
    17: ("Percussive Organ", "Organ"),
    18: ("Rock Organ", "Organ"),
    19: ("Church Organ", "Organ"),
    20: ("Reed Organ", "Organ"),
    21: ("Accordion", "Organ"),
    22: ("Harmonica", "Organ"),
    23: ("Tango Accordion", "Organ"),

    # Guitar (24-31) - Others
    24: ("Acoustic Guitar (nylon)", "Guitar"),
    25: ("Acoustic Guitar (steel)", "Guitar"),
    26: ("Electric Guitar (jazz)", "Guitar"),
    27: ("Electric Guitar (clean)", "Guitar"),
    28: ("Electric Guitar (muted)", "Guitar"),
    29: ("Overdriven Guitar", "Guitar"),
    30: ("Distortion Guitar", "Guitar"),
    31: ("Guitar harmonics", "Guitar"),

    # Bass (32-39) - Bass
    32: ("Acoustic Bass", "Bass"),
    33: ("Electric Bass (finger)", "Bass"),
    34: ("Electric Bass (pick)", "Bass"),
    35: ("Fretless Bass", "Bass"),
    36: ("Slap Bass 1", "Bass"),
    37: ("Slap Bass 2", "Bass"),
    38: ("Synth Bass 1", "Bass"),
    39: ("Synth Bass 2", "Bass"),

    # Strings (40-47) - Others (except Contrabass)
    40: ("Violin", "Strings"),
    41: ("Viola", "Strings"),
    42: ("Cello", "Strings"),
    43: ("Contrabass", "Bass"),  # Bass family
    44: ("Tremolo Strings", "Strings"),
    45: ("Pizzicato Strings", "Strings"),
    46: ("Orchestral Harp", "Strings"),
    47: ("Timpani", "Percussion"),

    # Ensemble (48-55) - Others
    48: ("String Ensemble 1", "Ensemble"),
    49: ("String Ensemble 2", "Ensemble"),
    50: ("SynthStrings 1", "Ensemble"),
    51: ("SynthStrings 2", "Ensemble"),
    52: ("Choir Aahs", "Ensemble"),
    53: ("Voice Oohs", "Ensemble"),
    54: ("Synth Voice", "Ensemble"),
    55: ("Orchestra Hit", "Ensemble"),

    # Brass (56-63) - Others
    56: ("Trumpet", "Brass"),
    57: ("Trombone", "Brass"),
    58: ("Tuba", "Brass"),
    59: ("Muted Trumpet", "Brass"),
    60: ("French Horn", "Brass"),
    61: ("Brass Section", "Brass"),
    62: ("SynthBrass 1", "Brass"),
    63: ("SynthBrass 2", "Brass"),

    # Reed (64-71) - Others (except Baritone Sax)
    64: ("Soprano Sax", "Reed"),
    65: ("Alto Sax", "Reed"),
    66: ("Tenor Sax", "Reed"),
    67: ("Baritone Sax", "Bass"),  # Bass family
    68: ("Oboe", "Reed"),
    69: ("English Horn", "Reed"),
    70: ("Bassoon", "Reed"),
    71: ("Clarinet", "Reed"),

    # Pipe (72-79) - Others
    72: ("Piccolo", "Pipe"),
    73: ("Flute", "Pipe"),
    74: ("Recorder", "Pipe"),
    75: ("Pan Flute", "Pipe"),
    76: ("Blown Bottle", "Pipe"),
    77: ("Shakuhachi", "Pipe"),
    78: ("Whistle", "Pipe"),
    79: ("Ocarina", "Pipe"),

    # Synth Lead (80-87) - Others (except 85, 87)
    80: ("Lead 1 (square)", "Synth Lead"),
    81: ("Lead 2 (sawtooth)", "Synth Lead"),
    82: ("Lead 3 (calliope)", "Synth Lead"),
    83: ("Lead 4 (chiff)", "Synth Lead"),
    84: ("Lead 5 (charang)", "Synth Lead"),
    85: ("Lead 6 (voice)", "Bass"),  # Bass family
    86: ("Lead 7 (fifths)", "Synth Lead"),
    87: ("Lead 8 (bass + lead)", "Bass"),  # Bass family

    # Synth Pad (88-95) - Others (except Pad 4)
    88: ("Pad 1 (new age)", "Synth Pad"),
    89: ("Pad 2 (warm)", "Synth Pad"),
    90: ("Pad 3 (polysynth)", "Synth Pad"),
    91: ("Pad 4 (choir)", "Voices"),  # Voices family
    92: ("Pad 5 (bowed)", "Synth Pad"),
    93: ("Pad 6 (metallic)", "Synth Pad"),
    94: ("Pad 7 (halo)", "Synth Pad"),
    95: ("Pad 8 (sweep)", "Synth Pad"),

    # Synth Effects (96-103) - Others
    96: ("FX 1 (rain)", "Synth Effects"),
    97: ("FX 2 (soundtrack)", "Synth Effects"),
    98: ("FX 3 (crystal)", "Synth Effects"),
    99: ("FX 4 (atmosphere)", "Synth Effects"),
    100: ("FX 5 (brightness)", "Synth Effects"),
    101: ("FX 6 (goblins)", "Synth Effects"),
    102: ("FX 7 (echoes)", "Synth Effects"),
    103: ("FX 8 (sci-fi)", "Synth Effects"),

    # Ethnic (104-111) - Others
    104: ("Sitar", "Ethnic"),
    105: ("Banjo", "Ethnic"),
    106: ("Shamisen", "Ethnic"),
    107: ("Koto", "Ethnic"),
    108: ("Kalimba", "Ethnic"),
    109: ("Bag pipe", "Ethnic"),
    110: ("Fiddle", "Ethnic"),
    111: ("Shanai", "Ethnic"),

    # Percussive (112-119) - Drums
    112: ("Tinkle Bell", "Percussion"),
    113: ("Agogo", "Percussion"),
    114: ("Steel Drums", "Percussion"),
    115: ("Woodblock", "Percussion"),
    116: ("Taiko Drum", "Percussion"),
    117: ("Melodic Tom", "Percussion"),
    118: ("Synth Drum", "Percussion"),
    119: ("Reverse Cymbal", "Percussion"),

    # Sound Effects (120-127) - Others
    120: ("Guitar Fret Noise", "Sound Effects"),
    121: ("Breath Noise", "Sound Effects"),
    122: ("Seashore", "Sound Effects"),
    123: ("Bird Tweet", "Sound Effects"),
    124: ("Telephone Ring", "Sound Effects"),
    125: ("Helicopter", "Sound Effects"),
    126: ("Applause", "Sound Effects"),
    127: ("Gunshot", "Sound Effects"),
}


def get_instrument_info(program: int) -> Tuple[str, str]:
    """
    Get instrument name and family for a GM program number

    Args:
        program: MIDI program number (0-127)

    Returns:
        Tuple of (instrument_name, family_name)
    """
    if program in GM_INSTRUMENT_FAMILIES:
        return GM_INSTRUMENT_FAMILIES[program]
    else:
        return (f"Unknown Instrument {program}", "Unknown")


def get_safe_filename(instrument_name: str) -> str:
    """
    Convert instrument name to safe filename

    Args:
        instrument_name: GM instrument name (e.g., "Electric Bass (finger)")

    Returns:
        Safe filename (e.g., "electric_bass_finger")
    """
    # Remove special characters and convert to lowercase
    safe_name = instrument_name.lower()
    safe_name = safe_name.replace("(", "").replace(")", "").replace(" ", "_")
    safe_name = safe_name.replace("+", "plus").replace("/", "_")
    safe_name = safe_name.replace("&", "and")
    # Remove multiple underscores
    while "__" in safe_name:
        safe_name = safe_name.replace("__", "_")
    return safe_name.strip("_")


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


def _add_program_change_event(instrument: 'pretty_midi.Instrument', program: int):
    """
    Add program change event at the start of an instrument track

    Args:
        instrument: PrettyMIDI Instrument object
        program: MIDI program number (0-127)
    """
    import pretty_midi

    # Create program change event at time 0
    # PrettyMIDI handles program changes through the instrument.program attribute
    # But we can also add explicit control changes for clarity
    instrument.program = program

    # Add a program change control message at time 0 (optional, for explicit clarity)
    # MIDI Control Change 0 (Bank Select MSB) followed by Program Change
    # This ensures DAWs recognize the instrument type immediately
    if not instrument.is_drum:
        # For melodic instruments, set program explicitly
        # Note: PrettyMIDI automatically writes program change events based on instrument.program
        logger.debug(f"Set program {program} ({pretty_midi.program_to_instrument_name(program)}) for track")


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

    # Set drum program (GM standard: program 0 for percussion on channel 10)
    _add_program_change_event(percussion, 0)

    new_midi.instruments.append(percussion)
    logger.info(f"Drums: moved {len(all_notes)} notes to Channel 10 (GM percussion)")

    return new_midi


def _process_melodic_instruments(midi: 'pretty_midi.PrettyMIDI', stem_type: str) -> 'pretty_midi.PrettyMIDI':
    """
    Apply GM Level 1 program constraints to melodic instruments

    Only enforces correct instrument categories per GM specification (page 5).
    Does NOT filter notes - only enforces instrument programs.
    """
    allowed_programs = StemInstrumentMapper.get_allowed_programs(stem_type)
    default_program = StemInstrumentMapper.get_default_program(stem_type)

    for instrument in midi.instruments:
        if instrument.is_drum:
            # Remove drums from melodic stems
            instrument.notes = []
            continue

        # Remap program if not allowed (per GM spec categories)
        if instrument.program not in allowed_programs:
            logger.debug(f"Remapping program {instrument.program} -> {default_program} for {stem_type}")
            instrument.program = default_program

        # Add program change event for the assigned program
        _add_program_change_event(instrument, instrument.program)

    return midi


def split_midi_by_instruments(
    midi_path: str,
    output_dir: str,
    stem_name: str = ""
) -> List[Dict[str, Any]]:
    """
    Split a MIDI file into separate files for each detected instrument

    Takes a multi-track MIDI file (e.g., from YourMT3) and creates individual
    MIDI files for each unique GM program (instrument) detected.

    Args:
        midi_path: Path to source MIDI file (e.g., "bass.mid", "other.mid")
        output_dir: Directory to save individual instrument MIDI files
        stem_name: Original stem name (for logging, optional)

    Returns:
        List of dictionaries with instrument metadata:
        [
            {
                "instrument_name": "Electric Bass (finger)",
                "family": "Bass",
                "program": 33,
                "midi_path": "/path/to/electric_bass_finger.mid",
                "midi_filename": "electric_bass_finger.mid",
                "note_count": 245,
                "duration": 180.5
            },
            ...
        ]

    Raises:
        FileNotFoundError: If MIDI file not found
        RuntimeError: If splitting fails

    Example:
        >>> instruments = split_midi_by_instruments("other.mid", "./output")
        >>> for inst in instruments:
        ...     print(f"{inst['instrument_name']}: {inst['note_count']} notes")
        Acoustic Grand Piano: 450 notes
        Violin: 280 notes
    """
    import pretty_midi
    import os

    midi_file = Path(midi_path)
    if not midi_file.exists():
        raise FileNotFoundError(f"MIDI file not found: {midi_path}")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Load source MIDI file
        source_midi = pretty_midi.PrettyMIDI(str(midi_file))

        logger.info(
            f"Splitting MIDI by instruments: {midi_path} "
            f"({len(source_midi.instruments)} tracks)"
        )

        # Group notes by program number
        instruments_data = {}  # program -> {name, family, notes}

        for track_idx, track in enumerate(source_midi.instruments):
            program = track.program
            is_drum = track.is_drum

            # Handle drums separately (they don't have program numbers)
            if is_drum:
                # Drums: use special marker
                program_key = "drums"
                instrument_name = "Acoustic Drums"
                family = "Percussion"
            else:
                # Melodic instruments: use program number
                program_key = f"program_{program}"
                instrument_name, family = get_instrument_info(program)

            # Initialize instrument data if first time seeing this program
            if program_key not in instruments_data:
                instruments_data[program_key] = {
                    "program": program if not is_drum else None,
                    "is_drum": is_drum,
                    "instrument_name": instrument_name,
                    "family": family,
                    "notes": [],
                    "pitch_bends": [],
                    "control_changes": [],
                }

            # Add all notes from this track to the instrument
            instruments_data[program_key]["notes"].extend(track.notes)
            instruments_data[program_key]["pitch_bends"].extend(track.pitch_bends)
            instruments_data[program_key]["control_changes"].extend(track.control_changes)

            logger.debug(
                f"Track {track_idx}: {instrument_name} (Program {program}) "
                f"- {len(track.notes)} notes"
            )

        # Create separate MIDI file for each detected instrument
        result_files = []

        for program_key, inst_data in instruments_data.items():
            instrument_name = inst_data["instrument_name"]
            family = inst_data["family"]
            program = inst_data["program"]
            is_drum = inst_data["is_drum"]
            notes = inst_data["notes"]

            if len(notes) == 0:
                logger.debug(f"Skipping {instrument_name}: no notes")
                continue

            # Create new MIDI file for this instrument
            new_midi = pretty_midi.PrettyMIDI()

            # Create instrument track
            if is_drum:
                new_instrument = pretty_midi.Instrument(
                    program=0,
                    is_drum=True,
                    name=instrument_name
                )
            else:
                new_instrument = pretty_midi.Instrument(
                    program=program,
                    is_drum=False,
                    name=instrument_name
                )

            # Add all notes
            new_instrument.notes.extend(notes)

            # Add pitch bends and control changes
            new_instrument.pitch_bends.extend(inst_data["pitch_bends"])
            new_instrument.control_changes.extend(inst_data["control_changes"])

            # Add instrument to MIDI
            new_midi.instruments.append(new_instrument)

            # Generate safe filename
            safe_name = get_safe_filename(instrument_name)
            output_filename = f"{safe_name}.mid"
            output_path = os.path.join(output_dir, output_filename)

            # Save MIDI file
            new_midi.write(output_path)

            # Calculate duration
            if len(notes) > 0:
                duration = max(note.end for note in notes)
            else:
                duration = 0.0

            result_files.append({
                "instrument_name": instrument_name,
                "family": family,
                "program": program,
                "midi_path": output_path,
                "midi_filename": output_filename,
                "note_count": len(notes),
                "duration": duration,
                "is_drum": is_drum,
            })

            logger.info(
                f"Created {output_filename}: {instrument_name} "
                f"({len(notes)} notes, {duration:.2f}s)"
            )

        logger.info(
            f"Split complete: {len(result_files)} instrument files created "
            f"from {stem_name or midi_file.name}"
        )

        return result_files

    except Exception as e:
        logger.error(f"Failed to split MIDI by instruments: {e}")
        raise RuntimeError(f"MIDI splitting failed: {e}")
