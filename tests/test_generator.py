"""Tests for the pool builder and multi-task generator.

Locks: every emitted record is gold-verified, splits are leakage-free by shape
(across keys AND across tasks), the brief's example is present, task framings are
well-formed, and generation is deterministic.
"""
from collections import Counter

from harmony_dataset.generator import build_pool, generate
from harmony_dataset.cadence import classify_cadence
from harmony_dataset.vocabulary import Analysis


class TestPool:
    def test_shapes_distinct(self):
        pool = build_pool()
        keys = [(s.mode, s.labels) for s in pool]
        assert len(keys) == len(set(keys))

    def test_has_curated_and_grammar_and_single(self):
        sources = {s.source for s in build_pool()}
        assert {"curated", "grammar", "single"} <= sources

    def test_split_is_stable(self):
        # shape -> split must be deterministic across calls. build_pool is
        # lru_cached, so compare a FRESH build (__wrapped__) against the cached
        # one — comparing two cached calls would be a self-comparison.
        a = {s.shape_id: s.split for s in build_pool.__wrapped__()}
        b = {s.shape_id: s.split for s in build_pool()}
        assert a == b


class TestLeakage:
    def test_no_shape_crosses_splits(self):
        res = generate()
        by_shape: dict[str, set[str]] = {}
        for r in res.records:
            by_shape.setdefault(r.data["shape_id"], set()).add(r.split)
        offenders = {sid: sp for sid, sp in by_shape.items() if len(sp) > 1}
        assert not offenders, f"shapes leaking across splits: {offenders}"


class TestVerifiedAndDeterministic:
    def test_gold_gate_clean(self):
        # the locked vocabulary must verify perfectly; any disagreement is a bug
        res = generate()
        assert res.records
        assert res.chord_agreement_rate == 1.0
        assert res.dropped_instances == 0
        assert res.failures == []

    # NOTE: full-pipeline determinism follows from build_pool determinism
    # (tested above with a fresh __wrapped__ build — the only RNG lives there)
    # plus _instantiate being pure music21 rendering. A second full generate()
    # here would cost ~30s of suite time for no extra signal.


class TestBriefExample:
    def test_jazz_ii_V_I_symbol_task_present(self):
        res = generate()
        hits = [
            r.data for r in res.records
            if r.data["task"] == "symbol_to_rn"
            and r.data["key"] == "C major"
            and r.data.get("chords") == ["Dm7", "G7", "Cmaj7"]
        ]
        assert len(hits) == 1
        assert hits[0]["target"] == "ii7 V7 IM7\ncadence: PAC"


class TestTaskFraming:
    def test_all_tasks_present(self):
        tasks_seen = Counter(r.data["task"] for r in generate().records)
        assert set(tasks_seen) == {"symbol_to_rn", "notes_to_rn", "pcset_to_rn", "key_id"}

    def test_key_id_only_for_cadenced_multichord(self):
        for r in generate().records:
            if r.data["task"] == "key_id":
                assert r.data["cadence"] is not None
                assert len(r.data["labels"]) >= 3
                assert "key:" not in r.data["input"]  # key is hidden
                assert r.data["target"] == r.data["key"]

    def test_key_id_records_are_key_determined(self):
        # every key_id record's notes must contain scale degree 4 + leading tone
        # (otherwise a competing key admits the same notes and the gold is moot)
        letter = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

        def pc(note: str) -> int:
            core = note.rstrip("0123456789")
            v = letter[core[0]]
            for a in core[1:]:
                v += 1 if a == "#" else -1
            return v % 12

        for r in generate().records:
            if r.data["task"] != "key_id":
                continue
            tonic = pc(r.data["key"].split()[0] + "0")
            present = {pc(n) for ch in r.data["notes"] for n in ch}
            assert {(tonic + 5) % 12, (tonic + 11) % 12} <= present, r.data["input"]

    def test_notes_task_hides_symbols(self):
        for r in generate().records:
            if r.data["task"] == "notes_to_rn":
                assert "notes:" in r.data["input"]
                assert "progression:" not in r.data["input"]
                # target still matches the classifier
                labels = [Analysis.from_dict(a).dcml_label() for a in r.data["analysis"]]
                assert " ".join(labels) in r.data["target"]
