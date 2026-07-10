"""Tests for the probabilistic functional-harmony grammar.

The grammar must produce musically-shaped phrases: start on tonic, end on a
recognised cadence, and (crucially) every chord must survive the gold gate when
rendered in a key. It must be deterministic under a seed and genuinely diverse.
"""
from music21 import key

from harmony_dataset.grammar import generate_phrases
from harmony_dataset.cadence import classify_cadence
from harmony_dataset.verify import verify_chord
from harmony_dataset.vocabulary import Analysis, chord_symbol_from_figure


class TestParseSpec:
    def test_specs_round_trip_to_labels(self):
        assert Analysis.parse("ii7").dcml_label() == "ii7"
        assert Analysis.parse("IM7").dcml_label() == "IM7"
        assert Analysis.parse("iio6").dcml_label() == "iio6"
        assert Analysis.parse("ii%65").dcml_label() == "ii%65"
        assert Analysis.parse("V7/V").dcml_label() == "V7/V"
        assert Analysis.parse("viio7").dcml_label() == "viio7"


class TestPhraseShape:
    def test_starts_on_tonic(self):
        for mode in ("major", "minor"):
            for phrase in generate_phrases(mode, 40, seed=1):
                assert phrase[0].numeral in {"I", "i"}
                assert phrase[0].relativeroot is None

    def test_ends_on_cadence(self):
        for mode in ("major", "minor"):
            for phrase in generate_phrases(mode, 40, seed=2):
                assert classify_cadence(phrase) is not None

    def test_reasonable_length(self):
        for phrase in generate_phrases("major", 40, seed=3):
            assert 2 <= len(phrase) <= 9


class TestGoldGateCompatibility:
    def test_every_chord_verifies_in_reference_key(self):
        # nothing the grammar emits should fail the dual-derivation check
        for mode, k in (("major", "C"), ("minor", "a")):
            K = key.Key(k)
            for phrase in generate_phrases(mode, 60, seed=4):
                for a in phrase:
                    sym = chord_symbol_from_figure(a.music21_figure(), K)
                    assert verify_chord(a, sym, K).ok, f"{a.dcml_label()} -> {sym} in {k}"


class TestDeterminismAndDiversity:
    def test_deterministic(self):
        a = [tuple(p.dcml_label() for p in ph) for ph in generate_phrases("major", 30, seed=7)]
        b = [tuple(p.dcml_label() for p in ph) for ph in generate_phrases("major", 30, seed=7)]
        assert a == b

    def test_distinct_shapes(self):
        shapes = {tuple(p.dcml_label() for p in ph) for ph in generate_phrases("major", 120, seed=9)}
        # the grammar should yield real variety, not a handful of templates
        assert len(shapes) >= 40

    def test_uses_secondary_dominants(self):
        seen = set()
        for mode in ("major", "minor"):
            for ph in generate_phrases(mode, 150, seed=11):
                for a in ph:
                    if a.relativeroot is not None:
                        seen.add(a.dcml_label())
        assert seen, "grammar never produced a secondary dominant"
