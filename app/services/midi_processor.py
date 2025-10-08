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


def apply_stem_constraints(program: int, stem_type: str) -> int:
    """
    Apply GM MIDI program constraints based on stem type

    Corrects instrument classifications that don't match the stem source.
    Based on GM Classification session decisions.

    Args:
        program: Original MIDI program number (0-127)
        stem_type: Stem type ('bass', 'drums', 'other', 'vocals')

    Returns:
        Corrected MIDI program number

    Example:
        >>> # Piano (0) detected on bass stem -> correct to Electric Bass (33)
        >>> corrected = apply_stem_constraints(0, 'bass')
        >>> assert corrected == 33
    """
    if stem_type == 'bass':
        # Bass stem: Programs 32-39 (GM Bass family)
        # If prediction is outside bass range, default to Electric Bass (finger)
        if program < 32 or program > 39:
            logger.info(f"Correcting program {program} -> 33 (Electric Bass) for bass stem")
            return 33  # Electric Bass (finger)
        return program

    elif stem_type == 'drums':
        # Drums stem: Programs 113-120 or is_drum=True
        # Melodic drums should be in this range
        if program < 113 or program > 120:
            # If non-drum program on drum stem, map to Synth Drum
            logger.info(f"Correcting program {program} -> 118 (Synth Drum) for drums stem")
            return 118  # Synth Drum
        return program

    elif stem_type == 'other':
        # Others stem: Programs 1-32, 41-112, 121-128
        # Most instruments allowed, minimal constraints
        # Sound effects (121-128) unlikely to be transcribed by MT3
        return program

    elif stem_type == 'vocals':
        # Vocals: VAD only in v1.0, no MIDI output
        # Future: speech-to-text
        return program

    return program
