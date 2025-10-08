"""
Unit tests for MIDI processor service
"""

import pytest
from app.services.midi_processor import apply_stem_constraints


class TestStemConstraints:
    """Test GM MIDI program constraints for different stems"""

    def test_bass_stem_constraint_correction(self):
        """Test bass stem corrects non-bass programs to 33"""
        # Piano (0) on bass stem should correct to Electric Bass (33)
        assert apply_stem_constraints(0, 'bass') == 33

        # String (40) on bass stem should correct to Electric Bass (33)
        assert apply_stem_constraints(40, 'bass') == 33

        # Valid bass program should remain unchanged
        assert apply_stem_constraints(33, 'bass') == 33
        assert apply_stem_constraints(35, 'bass') == 35
        assert apply_stem_constraints(39, 'bass') == 39

    def test_bass_stem_program_range(self):
        """Test all valid bass programs (33-40) remain unchanged"""
        for program in range(33, 41):
            assert apply_stem_constraints(program, 'bass') == program

    def test_drums_stem_constraint_correction(self):
        """Test drums stem corrects non-drum programs to 118"""
        # Piano (0) on drums stem should correct to Synth Drum (118)
        assert apply_stem_constraints(0, 'drums') == 118

        # Bass (33) on drums stem should correct to Synth Drum (118)
        assert apply_stem_constraints(33, 'drums') == 118

        # Valid drum program should remain unchanged
        assert apply_stem_constraints(113, 'drums') == 113
        assert apply_stem_constraints(118, 'drums') == 118
        assert apply_stem_constraints(119, 'drums') == 119

    def test_drums_stem_program_range(self):
        """Test all valid drum programs (113-120) remain unchanged"""
        for program in range(113, 121):
            assert apply_stem_constraints(program, 'drums') == program

    def test_other_stem_no_constraints(self):
        """Test other stem allows all programs"""
        # Piano family
        assert apply_stem_constraints(0, 'other') == 0

        # Guitar family
        assert apply_stem_constraints(25, 'other') == 25

        # Bass (should be allowed in 'other' even though uncommon)
        assert apply_stem_constraints(33, 'other') == 33

        # Strings
        assert apply_stem_constraints(48, 'other') == 48

        # Synth
        assert apply_stem_constraints(80, 'other') == 80

        # Sound effects
        assert apply_stem_constraints(125, 'other') == 125

    def test_vocals_stem_passthrough(self):
        """Test vocals stem doesn't modify programs (VAD only)"""
        # Vocals stem shouldn't have MIDI output in v1.0, but if it does, pass through
        assert apply_stem_constraints(0, 'vocals') == 0
        assert apply_stem_constraints(53, 'vocals') == 53  # Choir Aahs

    def test_edge_cases(self):
        """Test boundary conditions"""
        # Program 32 is outside bass range (should correct to 33)
        assert apply_stem_constraints(32, 'bass') == 33

        # Program 40 is outside bass range (should correct to 33)
        assert apply_stem_constraints(40, 'bass') == 33

        # Program 112 is outside drum range (should correct to 118)
        assert apply_stem_constraints(112, 'drums') == 118

        # Program 120 is outside drum range (should correct to 118)
        assert apply_stem_constraints(120, 'drums') == 118

    def test_constraint_logic_matches_specification(self):
        """
        Verify constraints match GM Classification specification

        From SESSION_2025-10-07_GM_Classification.md:
        - Bass: Programs 33-40
        - Drums: Programs 113-120
        - Other: Programs 1-32, 41-112, 121-128
        - Vocals: VAD only (no MIDI)
        """
        # Bass constraints
        assert apply_stem_constraints(0, 'bass') == 33  # Non-bass → default bass
        assert apply_stem_constraints(35, 'bass') == 35  # Bass → unchanged

        # Drums constraints
        assert apply_stem_constraints(0, 'drums') == 118  # Non-drum → default drum
        assert apply_stem_constraints(115, 'drums') == 115  # Drum → unchanged

        # Other: minimal constraints
        for program in [0, 25, 50, 75, 100, 125]:
            assert apply_stem_constraints(program, 'other') == program
