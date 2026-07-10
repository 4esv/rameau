"""Cadence classification into DCML cadence codes.

music21 ships no cadence detector (only building blocks), so this is ours. It
looks at the last two chords of an Analysis sequence and classifies the terminal
cadence:

    PAC  perfect authentic   V(7) -> I/i, both root position
    IAC  imperfect authentic V(7) -> I/i, dominant or tonic inverted
    HC   half                phrase ends on a root-position diatonic V *triad*
                             (a terminal V7 demands resolution and is not an HC)
    PC   plagal              IV/iv -> I/i
    DC   deceptive           root-position V(7) -> vi/VI (an inverted dominant's
                             bass must resolve to the tonic, so V65 -> vi is a
                             voice-leading error, not a deceptive cadence)
    None no terminal cadence

Simplification: with synthetic root-position chord symbols we have no soprano
voice, so PAC vs IAC is decided by inversion rather than by melodic closure.
"""
from __future__ import annotations

from typing import Optional

from .vocabulary import Analysis

_TONIC = frozenset({"I", "i"})
_DOMINANT = frozenset({"V"})
_SUBDOMINANT = frozenset({"IV", "iv"})
_SUBMEDIANT = frozenset({"vi", "VI"})

# figbass values that denote a root-position chord (triad '' or root seventh '7')
_ROOT_POSITION = frozenset({"", "7"})


def _is_diatonic(a: Analysis) -> bool:
    return a.relativeroot is None


def _is_root_position(a: Analysis) -> bool:
    return a.figbass in _ROOT_POSITION


def _is(a: Analysis, degrees: frozenset[str]) -> bool:
    return _is_diatonic(a) and a.numeral in degrees


def classify_cadence(seq: list[Analysis]) -> Optional[str]:
    if len(seq) < 2:
        return None
    penult, last = seq[-2], seq[-1]

    if _is(last, _TONIC):
        if _is(penult, _DOMINANT):
            return "PAC" if _is_root_position(penult) and _is_root_position(last) else "IAC"
        if _is(penult, _SUBDOMINANT):
            return "PC"
        return None

    if _is(last, _SUBMEDIANT) and _is(penult, _DOMINANT) and _is_root_position(penult):
        return "DC"

    if _is(last, _DOMINANT) and last.figbass == "":
        return "HC"

    return None
