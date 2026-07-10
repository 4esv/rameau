"""Tests for the task framings, especially the key_id determinacy gate."""
import pytest

from harmony_dataset.tasks import render, _key_is_determined

# the brief example: ii7 V7 IM7 in C major
_ARGS = dict(
    key="C major",
    symbols=["Dm7", "G7", "Cmaj7"],
    notes=[["D4", "F4", "A4", "C5"], ["G4", "B4", "D5", "F5"], ["C4", "E4", "G4", "B4"]],
    pcs=[[2, 5, 9, 0], [7, 11, 2, 5], [0, 4, 7, 11]],
    labels=["ii7", "V7", "IM7"],
    cadence="PAC",
)


class TestFormats:
    def test_symbol(self):
        r = render("symbol_to_rn", **_ARGS)
        assert r.input == "key: C major\nprogression: Dm7 G7 Cmaj7"
        assert r.target == "ii7 V7 IM7\ncadence: PAC"

    def test_notes(self):
        r = render("notes_to_rn", **_ARGS)
        assert "notes: D4 F4 A4 C5 | G4 B4 D5 F5 | C4 E4 G4 B4" in r.input

    def test_pcset(self):
        r = render("pcset_to_rn", **_ARGS)
        assert "pitch classes: [2 5 9 0] | [7 11 2 5] | [0 4 7 11]" in r.input

    def test_unknown_task_raises(self):
        with pytest.raises(ValueError):
            render("nope", **_ARGS)


class TestKeyIdGate:
    def test_determined_case_passes(self):
        r = render("key_id", **_ARGS)
        assert r is not None
        assert r.target == "C major"
        assert "key:" not in r.input

    def test_smoking_gun_excluded(self):
        # I V7/V V in C == IV V7 I in G (note-identical, stronger reading).
        # No scale degree 4 (F) anywhere -> key not determined -> excluded.
        args = dict(_ARGS)
        args.update(
            symbols=["C", "D7", "G"],
            notes=[["C4", "E4", "G4"], ["D4", "F#4", "A4", "C5"], ["G4", "B4", "D5"]],
            pcs=[[0, 4, 7], [2, 6, 9, 0], [7, 11, 2]],
            labels=["I", "V7/V", "V"],
            cadence="HC",
        )
        assert render("key_id", **args) is None

    def test_plagal_without_leading_tone_excluded(self):
        # I IV I in C == V I V in F: ambiguous, no B anywhere.
        args = dict(_ARGS)
        args.update(
            symbols=["C", "F", "C"],
            notes=[["C4", "E4", "G4"], ["F4", "A4", "C5"], ["C4", "E4", "G4"]],
            pcs=[[0, 4, 7], [5, 9, 0], [0, 4, 7]],
            labels=["I", "IV", "I"],
            cadence="PC",
        )
        assert render("key_id", **args) is None

    def test_no_cadence_excluded(self):
        args = dict(_ARGS, cadence=None)
        assert render("key_id", **args) is None

    def test_too_short_excluded(self):
        args = dict(_ARGS)
        args.update(symbols=["G7", "C"], notes=_ARGS["notes"][1:], pcs=_ARGS["pcs"][1:],
                    labels=["V7", "I"], cadence="PAC")
        assert render("key_id", **args) is None


class TestDeterminacyHelper:
    def test_tritone_rule(self):
        # C major needs F (5) and B (11)
        assert _key_is_determined("C major", [[0, 4, 7], [5, 9, 0], [7, 11, 2]])
        assert not _key_is_determined("C major", [[0, 4, 7], [7, 11, 2]])       # no F
        assert not _key_is_determined("C major", [[0, 4, 7], [5, 9, 0]])        # no B

    def test_accidental_keys(self):
        # Ab major: degree 4 = Db (1), leading tone = G (7)
        assert _key_is_determined("Ab major", [[8, 0, 3], [1, 5, 8], [3, 7, 10]])
        # F# minor: degree 4 = B (11), leading tone = E# (5)
        assert _key_is_determined("F# minor", [[6, 9, 1], [11, 2, 6], [1, 5, 8]])