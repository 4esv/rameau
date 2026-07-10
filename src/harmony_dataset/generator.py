"""Build the full dataset: a pool of distinct progression shapes (curated anchors
+ grammar-generated phrases), transposed across keys, gold-gated, and framed as
multiple tasks.

Leakage control: the atomic unit is a **shape** — a key-independent tuple of
Roman-numeral labels. Each shape is hashed to exactly one split, so no shape (and
none of its transpositions, and none of its task framings) ever crosses splits.
The hash is stable (sha1), so splits are reproducible.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from music21 import key

from . import tasks
from .cadence import classify_cadence
from .grammar import generate_phrases
from .vocabulary import (
    Analysis,
    MAJOR_KEYS,
    MINOR_KEYS,
    bass_first_pcs_from_figure,
    chord_symbol_from_figure,
    spelled_notes_from_figure,
)
from .verify import ChordCheck, verify_chord

# how many grammar phrases to draw per mode, and how many keys to transpose a
# multi-chord shape into (single chords always go to all 12).
N_PHRASES_PER_MODE = 400
KEYS_PER_SHAPE = 6
SEED = 20260709


def _spec(*s: str) -> tuple[Analysis, ...]:
    return tuple(Analysis.parse(x) for x in s)


# Curated anchors: pedagogically important progressions worth guaranteeing.
_CURATED: list[tuple[str, str, tuple[Analysis, ...]]] = [
    ("major", "cadence", _spec("ii7", "V7", "IM7")),      # the brief's jazz ii-V-I
    ("major", "cadence", _spec("ii7", "V7", "I")),
    ("major", "common", _spec("I", "IV", "V", "I")),
    ("major", "common", _spec("I", "vi", "IV", "V")),
    ("major", "common", _spec("I", "V", "vi", "IV")),
    ("major", "secondary", _spec("I", "V7/vi", "vi", "ii7", "V7", "I")),
    ("minor", "common", _spec("i", "VII", "VI", "V")),    # Andalusian
    ("minor", "cadence", _spec("iio6", "V7", "i")),
    ("minor", "common", _spec("i", "iv", "V", "i")),
]

# Single-chord vocabulary coverage (length-1 shapes).
_SINGLE_MAJOR = ["I", "ii", "iii", "IV", "V", "vi", "viio",
                 "IM7", "ii7", "iii7", "IVM7", "V7", "vi7", "vii%7",
                 "I6", "I64", "V6", "V65", "V43", "V2", "ii6"]
_SINGLE_MINOR = ["i", "iio", "III", "iv", "V", "VI", "viio",
                 "i7", "ii%7", "iv7", "V7", "VIM7", "viio7",
                 "i6", "i64", "V6", "V65", "V43", "iio6"]


@dataclass(frozen=True)
class Shape:
    mode: str
    category: str
    source: str            # 'curated' | 'grammar' | 'single'
    analyses: tuple[Analysis, ...]

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(a.dcml_label() for a in self.analyses)

    @property
    def shape_id(self) -> str:
        raw = f"{self.mode}|{','.join(self.labels)}"
        return hashlib.sha1(raw.encode()).hexdigest()[:10]

    @property
    def split(self) -> str:
        bucket = int(self.shape_id, 16) % 100
        return "train" if bucket < 70 else "validation" if bucket < 85 else "test"


@lru_cache(maxsize=1)
def build_pool() -> list[Shape]:
    """Distinct shapes: curated anchors, single chords, grammar phrases. Deduped."""
    pool: list[Shape] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()

    def add(shape: Shape) -> None:
        k = (shape.mode, shape.labels)
        if k not in seen:
            seen.add(k)
            pool.append(shape)

    for mode, cat, analyses in _CURATED:
        add(Shape(mode, cat, "curated", analyses))
    for spec in _SINGLE_MAJOR:
        add(Shape("major", "single", "single", _spec(spec)))
    for spec in _SINGLE_MINOR:
        add(Shape("minor", "single", "single", _spec(spec)))
    for mode in ("major", "minor"):
        for phrase in generate_phrases(mode, N_PHRASES_PER_MODE, seed=SEED):
            add(Shape(mode, "phrase", "grammar", tuple(phrase)))
    return pool


def _keys_for(shape: Shape) -> list[str]:
    keys = MAJOR_KEYS if shape.mode == "major" else MINOR_KEYS
    if len(shape.analyses) == 1:
        return keys
    # always include the reference key (C major / A minor) so canonical shapes
    # appear in their home key, then a hash-spread sample of others.
    ref = "C" if shape.mode == "major" else "a"
    offset = int(shape.shape_id, 16) % 12
    idxs = sorted({(offset + i * 5) % 12 for i in range(KEYS_PER_SHAPE)})
    ordered = [ref] + [keys[i] for i in idxs if keys[i] != ref]
    return ordered


@dataclass(frozen=True)
class Record:
    data: dict
    split: str


@dataclass
class Failure:
    shape_id: str
    key: str
    check: ChordCheck


@dataclass
class GenResult:
    records: list[Record] = field(default_factory=list)
    failures: list[Failure] = field(default_factory=list)
    shapes: int = 0
    instances: int = 0
    dropped_instances: int = 0
    attempted_chords: int = 0

    @property
    def chord_agreement_rate(self) -> float:
        if self.attempted_chords == 0:
            return 1.0
        return (self.attempted_chords - len(self.failures)) / self.attempted_chords


def _instantiate(shape: Shape, key_name: str) -> Optional[dict]:
    """Render a shape in a key and gold-gate it. Returns representation data or None."""
    K = key.Key(key_name)
    symbols, notes, pcs, checks = [], [], [], []
    for a in shape.analyses:
        fig = a.music21_figure()
        sym = chord_symbol_from_figure(fig, K)
        checks.append(verify_chord(a, sym, K))
        symbols.append(sym.replace("-", "b"))
        notes.append(spelled_notes_from_figure(fig, K))
        pcs.append(bass_first_pcs_from_figure(fig, K))
    if not all(c.ok for c in checks):
        return {"_failed": [c for c in checks if not c.ok]}
    return {
        "key": f"{K.tonic.name.replace('-', 'b')} {K.mode}",
        "symbols": symbols, "notes": notes, "pcs": pcs,
    }


@lru_cache(maxsize=1)
def generate() -> GenResult:
    res = GenResult()
    pool = build_pool()
    res.shapes = len(pool)
    for shape in pool:
        labels = list(shape.labels)
        cadence = classify_cadence(list(shape.analyses))
        analysis_dicts = [a.to_dict() for a in shape.analyses]
        for key_name in _keys_for(shape):
            res.instances += 1
            res.attempted_chords += len(shape.analyses)
            data = _instantiate(shape, key_name)
            if data is None or "_failed" in data:
                res.dropped_instances += 1
                for c in (data or {}).get("_failed", []):
                    res.failures.append(Failure(shape.shape_id, key_name, c))
                continue
            for task in tasks.TASKS:
                r = tasks.render(
                    task, key=data["key"], symbols=data["symbols"],
                    notes=data["notes"], pcs=data["pcs"], labels=labels, cadence=cadence,
                )
                if r is None:
                    continue
                record = {
                    "task": r.task,
                    "input": r.input,
                    "target": r.target,
                    "key": data["key"],
                    "mode": shape.mode,
                    "labels": labels,
                    "cadence": cadence,
                    "analysis": analysis_dicts,
                    "source": shape.source,
                    "category": shape.category,
                    "shape_id": shape.shape_id,
                    **r.extra,
                }
                res.records.append(Record(record, shape.split))
    return res
