"""Tests for the DCML label grammar and the music21 bridge.

These lock the representation decisions from the plan:
- DCML feature-decomposed labels (numeral / form / figbass / changes / relativeroot)
- the single divergence from music21 figures: half-diminished '%' (DCML) vs 'ø' (music21)
- Cmaj7 -> IM7 (clean maj7, which music21's analytic figure gets wrong as 'I7')
"""
from music21 import key

from harmony_dataset.vocabulary import (
    Analysis,
    pitch_classes_from_figure,
    pitch_classes_from_symbol,
    bass_pc_from_figure,
    bass_first_pcs_from_figure,
    spelled_notes_from_figure,
    chord_symbol_from_figure,
    MAJOR_KEYS,
    MINOR_KEYS,
)


class TestDCMLLabels:
    def test_plain_seventh(self):
        a = Analysis("ii", figbass="7")
        assert a.dcml_label() == "ii7"
        assert a.music21_figure() == "ii7"

    def test_major_seventh_is_M(self):
        # the crux: Cmaj7 -> IM7, NOT the music21 analytic 'I7'
        a = Analysis("I", form="M", figbass="7")
        assert a.dcml_label() == "IM7"
        assert a.music21_figure() == "IM7"

    def test_half_diminished_glyph_diverges(self):
        a = Analysis("ii", form="%", figbass="7")
        assert a.dcml_label() == "ii%7"       # DCML uses %
        assert a.music21_figure() == "iiø7"   # music21 uses ø

    def test_diminished_seventh(self):
        a = Analysis("vii", form="o", figbass="7")
        assert a.dcml_label() == "viio7"
        assert a.music21_figure() == "viio7"

    def test_secondary_dominant(self):
        a = Analysis("V", figbass="7", relativeroot="V")
        assert a.dcml_label() == "V7/V"
        assert a.music21_figure() == "V7/V"

    def test_inversion_figbass(self):
        a = Analysis("V", figbass="65")
        assert a.dcml_label() == "V65"

    def test_roundtrip_dict(self):
        a = Analysis("ii", form="%", figbass="65", relativeroot="V")
        assert Analysis.from_dict(a.to_dict()) == a


class TestPitchClasses:
    def test_figure_pitch_classes_c_major(self):
        K = key.Key("C")
        assert pitch_classes_from_figure("ii7", K) == frozenset({0, 2, 5, 9})
        assert pitch_classes_from_figure("V7", K) == frozenset({2, 5, 7, 11})
        assert pitch_classes_from_figure("IM7", K) == frozenset({0, 4, 7, 11})

    def test_symbol_pitch_classes(self):
        assert pitch_classes_from_symbol("Dm7") == frozenset({0, 2, 5, 9})
        assert pitch_classes_from_symbol("G7") == frozenset({2, 5, 7, 11})
        assert pitch_classes_from_symbol("Cmaj7") == frozenset({0, 4, 7, 11})

    def test_minor_key_raised_leading_tone(self):
        # V7 in A minor is E7 (G#), not Em7
        K = key.Key("a")
        assert pitch_classes_from_figure("V7", K) == frozenset({2, 4, 8, 11})

    def test_bass_pc_of_inversion(self):
        K = key.Key("C")
        # V65 = G7 in first inversion, bass = B (pc 11)
        assert bass_pc_from_figure("V65", K) == 11
        # root position V7, bass = G (pc 7)
        assert bass_pc_from_figure("V7", K) == 7


class TestRepresentations:
    def test_spelled_notes_bass_first(self):
        K = key.Key("C")
        assert spelled_notes_from_figure("ii7", K) == ["D4", "F4", "A4", "C5"]
        # first-inversion dominant seventh: bass is the third (B)
        assert spelled_notes_from_figure("V65", K)[0] == "B4"

    def test_spelled_notes_flats_use_b(self):
        # Eb minor VI = Cb major triad; must render 'Cb', never 'C-'
        notes = spelled_notes_from_figure("VI", key.Key("e-"))
        assert notes[0].startswith("Cb")
        assert all("-" not in n for n in notes)

    def test_bass_first_pcs_dedup_and_order(self):
        K = key.Key("C")
        assert bass_first_pcs_from_figure("ii7", K) == [2, 5, 9, 0]
        # V65 bass is B (pc 11) — inversion recoverable from first element
        assert bass_first_pcs_from_figure("V65", K)[0] == 11


class TestChordSymbolGeneration:
    def test_symbol_from_figure_major_key(self):
        K = key.Key("C")
        assert chord_symbol_from_figure("ii7", K) == "Dm7"
        assert chord_symbol_from_figure("V7", K) == "G7"
        assert chord_symbol_from_figure("IM7", K) == "Cmaj7"
        assert chord_symbol_from_figure("I", K) == "C"

    def test_symbol_from_figure_minor_key(self):
        K = key.Key("a")
        assert chord_symbol_from_figure("V7", K) == "E7"
        assert chord_symbol_from_figure("i", K) == "Am"


class TestKeyInventory:
    def test_twelve_of_each(self):
        assert len(MAJOR_KEYS) == 12
        assert len(MINOR_KEYS) == 12

    def test_all_pitch_classes_covered(self):
        maj_pcs = {key.Key(k).tonic.pitchClass for k in MAJOR_KEYS}
        min_pcs = {key.Key(k).tonic.pitchClass for k in MINOR_KEYS}
        assert maj_pcs == set(range(12))
        assert min_pcs == set(range(12))
