"""The task tiers — the same verified progression framed several ways.

The point is to *hide the answer* to varying degrees so the dataset trains and
tests real harmonic reasoning, not chord-symbol lookup:

    symbol_to_rn  key + chord symbols        -> RN + cadence   (easy; quality given)
    notes_to_rn   key + spelled notes        -> RN + cadence   (must read the chord)
    pcset_to_rn   key + bass-first pc lists   -> RN + cadence   (no spelling either)
    key_id        spelled notes (no key)     -> key            (infer the key)

Each is exposed as its own dataset config so a consumer can load exactly the tier
they want.

``key_id`` is determinacy-gated. A cadence and length alone do not pin a key:
``I V7/V V`` in C is note-identical to ``IV V7 I`` in G — a *stronger* reading —
so its gold label would be contestable. We therefore require the phrase's notes
to contain both key-defining degrees, scale degree 4 and the leading tone: that
tritone occurs in exactly one major diatonic collection, and the tonic-chord
third (present via the cadence/opening) settles major vs minor. Phrases failing
the gate are simply excluded from key_id (they remain in the other tasks, where
the key is given).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

TASKS = ("symbol_to_rn", "notes_to_rn", "pcset_to_rn", "key_id")

# key_id needs enough context to pin a key: a real cadence and >= 3 chords.
_KEY_ID_MIN_CHORDS = 3

_LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def _tonic_pc(key_str: str) -> int:
    """Pitch class of the tonic in a key string like 'Ab major' or 'F# minor'."""
    name = key_str.split()[0]
    pc = _LETTER_PC[name[0]]
    for ch in name[1:]:
        pc += 1 if ch == "#" else -1
    return pc % 12


def _key_is_determined(key: str, pcs: list[list[int]]) -> bool:
    """True when the notes contain scale degree 4 AND the leading tone."""
    tonic = _tonic_pc(key)
    present = {p for chord_pcs in pcs for p in chord_pcs}
    return {(tonic + 5) % 12, (tonic + 11) % 12} <= present


@dataclass(frozen=True)
class Rendered:
    task: str
    input: str
    target: str
    extra: dict  # the input-side representation, for transparency


def _rn_target(labels: list[str], cadence: Optional[str]) -> str:
    body = " ".join(labels)
    return f"{body}\ncadence: {cadence}" if cadence else body


def _notes_str(notes: list[list[str]]) -> str:
    return " | ".join(" ".join(ch) for ch in notes)


def _pcs_str(pcs: list[list[int]]) -> str:
    return " | ".join("[" + " ".join(str(p) for p in ch) + "]" for ch in pcs)


def render(
    task: str,
    *,
    key: str,
    symbols: list[str],
    notes: list[list[str]],
    pcs: list[list[int]],
    labels: list[str],
    cadence: Optional[str],
) -> Optional[Rendered]:
    """Render one task, or return None when the task does not apply to this item."""
    if task == "symbol_to_rn":
        return Rendered(task, f"key: {key}\nprogression: {' '.join(symbols)}",
                        _rn_target(labels, cadence), {"chords": symbols})

    if task == "notes_to_rn":
        return Rendered(task, f"key: {key}\nnotes: {_notes_str(notes)}",
                        _rn_target(labels, cadence), {"notes": notes})

    if task == "pcset_to_rn":
        return Rendered(task, f"key: {key}\npitch classes: {_pcs_str(pcs)}",
                        _rn_target(labels, cadence), {"pitch_classes": pcs})

    if task == "key_id":
        if cadence is None or len(labels) < _KEY_ID_MIN_CHORDS:
            return None
        if not _key_is_determined(key, pcs):
            return None
        return Rendered(task, f"notes: {_notes_str(notes)}", key, {"notes": notes})

    raise ValueError(f"unknown task {task!r}")
