"""Tests for the cadence classifier.

music21 has no cadence detector, so this is our own. It emits DCML cadence codes
(PAC / IAC / HC / DC / PC) from the tail of an Analysis sequence. Because the
synthetic data is root-position chord symbols with no notated voicing, PAC vs IAC
is decided by inversion (both chords root position => PAC) rather than by soprano
position — a documented simplification.
"""
from harmony_dataset.cadence import classify_cadence
from harmony_dataset.vocabulary import Analysis


def A(numeral, form="", figbass="", relativeroot=None):
    return Analysis(numeral, form=form, figbass=figbass, relativeroot=relativeroot)


class TestAuthentic:
    def test_pac_major(self):
        assert classify_cadence([A("ii", figbass="7"), A("V", figbass="7"), A("I")]) == "PAC"

    def test_pac_minor(self):
        assert classify_cadence([A("iv"), A("V"), A("i")]) == "PAC"

    def test_iac_tonic_inverted(self):
        assert classify_cadence([A("ii", figbass="7"), A("V", figbass="7"), A("I", figbass="6")]) == "IAC"

    def test_iac_dominant_inverted(self):
        assert classify_cadence([A("ii", figbass="7"), A("V", figbass="65"), A("I")]) == "IAC"


class TestOtherCadences:
    def test_half_cadence(self):
        assert classify_cadence([A("I"), A("IV"), A("V")]) == "HC"

    def test_half_cadence_after_secondary(self):
        # I - V7/V - V  is a tonicized half cadence: ends on diatonic V
        assert classify_cadence([A("I"), A("V", figbass="7", relativeroot="V"), A("V")]) == "HC"

    def test_plagal(self):
        assert classify_cadence([A("I"), A("IV"), A("I")]) == "PC"

    def test_plagal_minor(self):
        assert classify_cadence([A("i"), A("iv"), A("i")]) == "PC"

    def test_deceptive_major(self):
        assert classify_cadence([A("ii", figbass="7"), A("V", figbass="7"), A("vi")]) == "DC"

    def test_deceptive_minor(self):
        assert classify_cadence([A("iv"), A("V", figbass="7"), A("VI")]) == "DC"

    def test_inverted_dominant_is_not_deceptive(self):
        # V65 -> vi: the bass (leading tone) must resolve to tonic; not a DC
        assert classify_cadence([A("I"), A("V", figbass="65"), A("vi")]) is None


class TestNoCadence:
    def test_ends_on_predominant(self):
        assert classify_cadence([A("I"), A("IV"), A("ii", figbass="7")]) is None

    def test_single_chord(self):
        assert classify_cadence([A("I")]) is None

    def test_empty(self):
        assert classify_cadence([]) is None

    def test_inverted_dominant_is_not_half_cadence(self):
        # ending on an inverted V is too weak to call a half cadence
        assert classify_cadence([A("I"), A("V", figbass="6")]) is None

    def test_terminal_v7_is_not_half_cadence(self):
        # a half cadence ends on a V triad; a terminal V7 demands resolution
        assert classify_cadence([A("I"), A("IV"), A("V", figbass="7")]) is None
