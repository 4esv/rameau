"""The eval harness must parse leniently, score strictly, and give the oracle 100%."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "eval"))

from score import parse_key, parse_rn, score_key, score_rn  # noqa: E402


def _pairs(cases):
    return [(g, {"prediction": p}) for g, p in cases]


class TestParseRN:
    def test_clean_two_line(self):
        assert parse_rn("ii7 V7 IM7\ncadence: PAC") == (["ii7", "V7", "IM7"], "PAC")

    def test_no_cadence(self):
        assert parse_rn("VIM7") == (["VIM7"], None)

    def test_prose_then_fenced_answer(self):
        text = "Let me analyze this.\n```\nI ii6 I64 V\ncadence: HC\n```"
        assert parse_rn(text) == (["I", "ii6", "I64", "V"], "HC")

    def test_inline_cadence(self):
        assert parse_rn("ii7 V7 I cadence: PAC") == (["ii7", "V7", "I"], "PAC")

    def test_unicode_and_separators(self):
        assert parse_rn("iiø7 – V⁷ – vii°6\ncadence: IAC") == (
            ["ii%7", "V7", "viio6"],
            "IAC",
        )

    def test_case_is_preserved(self):
        labels, _ = parse_rn("i64 V i")
        assert labels == ["i64", "V", "i"]  # not I64 / I

    def test_garbage(self):
        assert parse_rn("") == (None, None)


class TestParseKey:
    def test_plain(self):
        assert parse_key("Eb major") == "Eb major"

    def test_prose_wrapped(self):
        assert parse_key("The key of this phrase is F# minor.") == "F# minor"

    def test_lowercase_tonic(self):
        assert parse_key("f# minor") == "F# minor"

    def test_last_match_wins(self):
        assert parse_key("This has a major sound at first, but it is B minor") == "B minor"

    def test_no_key(self):
        assert parse_key("I have no idea") is None


class TestScoreRN:
    GOLD = {"labels": ["ii7", "V7", "IM7"], "cadence": "PAC"}

    def test_mixed_batch(self):
        pairs = _pairs([
            (self.GOLD, "ii7 V7 IM7\ncadence: PAC"),   # perfect
            (self.GOLD, "ii7 V7 IM7\ncadence: IAC"),   # wrong cadence
            (self.GOLD, "ii7 V7 I\ncadence: PAC"),     # one wrong chord
            (self.GOLD, "no idea"),                     # unparseable-ish
        ])
        m = score_rn(pairs)
        assert m["n"] == 4
        assert m["exact"] == 0.25
        assert m["labels_exact"] == 0.5
        assert m["cadence_acc"] == 0.5  # garbage row has no cadence, misses PAC
        # 3 + 3 + 2 + 0 hits of 12 gold chords ("no" != "ii7", "idea" != "V7")
        assert m["chord_acc"] == round(8 / 12, 4)

    def test_none_cadence_matches(self):
        m = score_rn(_pairs([({"labels": ["VIM7"], "cadence": None}, "VIM7")]))
        assert m["exact"] == 1.0


class TestScoreKey:
    def test_mixed_batch(self):
        pairs = _pairs([
            ({"target": "C major"}, "C major"),
            ({"target": "Bb major"}, "Bb minor"),   # tonic right, mode wrong
            ({"target": "F# minor"}, "???"),        # parse failure
        ])
        m = score_key(pairs)
        assert m["exact"] == round(1 / 3, 4)
        assert m["tonic_acc"] == round(2 / 3, 4)
        assert m["mode_acc"] == round(1 / 3, 4)
        assert m["parse_failures"] == 1


class TestOracle:
    """Feeding gold targets back as predictions must score 100% everywhere.

    This round-trips every real test-split target through the response parser,
    so any formatting the parser can't recover is caught here.
    """

    def _oracle(self, config):
        path = REPO / "data" / config / "test.jsonl"
        gold = [json.loads(ln) for ln in path.open()]
        return [(g, {"prediction": g["target"]}) for g in gold]

    def test_rn_configs(self):
        for config in ("symbol_to_rn", "notes_to_rn", "pcset_to_rn"):
            m = score_rn(self._oracle(config))
            assert m["exact"] == 1.0, (config, m)
            assert m["parse_failures"] == 0

    def test_key_id(self):
        m = score_key(self._oracle("key_id"))
        assert m["exact"] == 1.0, m
        assert m["parse_failures"] == 0
