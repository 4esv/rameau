"""The gold gate: dual-derivation verification.

For each chord we derive pitch content two independent ways and require they
agree exactly (pitch-class set + bass):

    figure  -> music21 roman engine   -> pitches      (the label's meaning)
    symbol  -> music21 chord-symbol parser -> pitches  (what the model sees)

If they disagree, the Roman-numeral label and the printed chord symbol denote
different chords, so the training pair would be wrong. Such items are dropped
and surfaced in the verification report. This is what makes the synthetic gold
trustworthy without hand-labelling.
"""
from __future__ import annotations

from dataclasses import dataclass

from music21 import key

from .vocabulary import (
    Analysis,
    bass_pc_from_figure,
    bass_pc_from_symbol,
    pitch_classes_from_figure,
    pitch_classes_from_symbol,
)

# music21 returns this string when it cannot name a chord.
_UNIDENTIFIED = "Chord Symbol Cannot Be Identified"


@dataclass(frozen=True)
class ChordCheck:
    ok: bool
    figure: str
    symbol: str
    figure_pcs: frozenset[int]
    symbol_pcs: frozenset[int]
    reason: str = ""


def verify_chord(analysis: Analysis, symbol: str, key_obj: key.Key) -> ChordCheck:
    figure = analysis.music21_figure()
    fig_pcs = pitch_classes_from_figure(figure, key_obj)

    if not symbol or symbol == _UNIDENTIFIED:
        return ChordCheck(False, figure, symbol, fig_pcs, frozenset(), "unidentified chord symbol")

    try:
        sym_pcs = pitch_classes_from_symbol(symbol)
        sym_bass = bass_pc_from_symbol(symbol)
    except Exception as exc:  # music21 raises a variety of parse errors
        return ChordCheck(False, figure, symbol, fig_pcs, frozenset(), f"symbol parse error: {exc}")

    if fig_pcs != sym_pcs:
        return ChordCheck(False, figure, symbol, fig_pcs, sym_pcs, "pitch-class set mismatch")

    if bass_pc_from_figure(figure, key_obj) != sym_bass:
        return ChordCheck(False, figure, symbol, fig_pcs, sym_pcs, "bass mismatch (inversion)")

    return ChordCheck(True, figure, symbol, fig_pcs, sym_pcs)
