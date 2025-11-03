"""
Test script for instrument-based MIDI splitting feature

This script demonstrates the new instrument splitting functionality.
It takes a multi-track MIDI file and splits it into individual files per instrument.

Usage:
    python test_instrument_splitting.py <path_to_midi_file>

Example:
    python test_instrument_splitting.py uploads/test-job/midi/other.mid
"""

import sys
from pathlib import Path
from app.services.midi_processor import split_midi_by_instruments, get_instrument_info


def test_splitting(midi_path: str):
    """Test MIDI splitting on a file"""
    midi_file = Path(midi_path)

    if not midi_file.exists():
        print(f"❌ Error: MIDI file not found: {midi_path}")
        return

    print(f"🎵 Testing instrument splitting on: {midi_file.name}\n")

    # Create output directory
    output_dir = midi_file.parent / "instruments_test"
    output_dir.mkdir(exist_ok=True)

    try:
        # Split MIDI by instruments
        instruments = split_midi_by_instruments(
            midi_path=str(midi_file),
            output_dir=str(output_dir),
            stem_name=midi_file.stem
        )

        print(f"✅ Successfully split into {len(instruments)} instruments:\n")

        # Display results
        for idx, inst in enumerate(instruments, 1):
            print(f"{idx}. {inst['instrument_name']}")
            print(f"   Family: {inst['family']}")
            print(f"   Program: {inst['program']}")
            print(f"   Notes: {inst['note_count']}")
            print(f"   Duration: {inst['duration']:.2f}s")
            print(f"   File: {inst['midi_filename']}")
            print()

        print(f"📁 Output directory: {output_dir}")
        print(f"\n🎹 Families detected:")
        families = sorted(set(inst['family'] for inst in instruments))
        for family in families:
            count = sum(1 for inst in instruments if inst['family'] == family)
            print(f"   - {family}: {count} instrument(s)")

    except Exception as e:
        print(f"❌ Error during splitting: {e}")
        import traceback
        traceback.print_exc()


def show_gm_mapping():
    """Show General MIDI instrument mapping"""
    print("\n🎼 General MIDI Instrument Families:\n")

    families = {}
    for program in range(128):
        name, family = get_instrument_info(program)
        if family not in families:
            families[family] = []
        families[family].append((program, name))

    for family, instruments in sorted(families.items()):
        print(f"{family} ({len(instruments)} instruments):")
        for program, name in instruments[:3]:  # Show first 3
            print(f"   {program:3d}. {name}")
        if len(instruments) > 3:
            print(f"   ... and {len(instruments) - 3} more")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_instrument_splitting.py <midi_file_path>")
        print("\nExample:")
        print("  python test_instrument_splitting.py uploads/job-123/midi/other.mid")
        print("\nOr show GM mapping:")
        print("  python test_instrument_splitting.py --show-gm")
        sys.exit(1)

    if sys.argv[1] == "--show-gm":
        show_gm_mapping()
    else:
        test_splitting(sys.argv[1])
