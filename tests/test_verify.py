"""Tests for the dual-derivation gold gate.

A chord passes only if the pitch content implied by its Roman-numeral label
(rendered by music21's roman engine) matches the pitch content implied by its
printed chord symbol (parsed by music21's independent chord-symbol parser),
including the bass. Disagreement means the label and the symbol shown to the
model denote different chords — that item must never reach the dataset.
"""
from music21 import key

from harmony_dataset.vocabulary import Analysis
from harmony_dataset.verify import verify_chord


K = key.Key("C")


class TestPasses:
    def test_matching_chord(self):
        assert verify_chord(Analysis("ii", figbass="7"), "Dm7", K).ok

    def test_matching_maj7(self):
        assert verify_chord(Analysis("I", form="M", figbass="7"), "Cmaj7", K).ok

    def test_matching_inversion_bass(self):
        # V65 = G7/B; bass must line up too
        assert verify_chord(Analysis("V", figbass="65"), "G7/B", K).ok


class TestFails:
    def test_wrong_quality(self):
        # Dm7b5 (half-dim) != ii7 (minor 7)
        res = verify_chord(Analysis("ii", figbass="7"), "Dm7b5", K)
        assert not res.ok
        assert res.figure_pcs != res.symbol_pcs

    def test_wrong_bass(self):
        # right notes, wrong inversion: V7 (root) vs G7/B (first inversion)
        res = verify_chord(Analysis("V", figbass="7"), "G7/B", K)
        assert not res.ok
        assert "bass" in res.reason.lower()

    def test_unparseable_symbol(self):
        res = verify_chord(Analysis("V", figbass="7"), "not-a-chord", K)
        assert not res.ok
