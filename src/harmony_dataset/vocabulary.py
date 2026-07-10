"""DCML label grammar and the music21 bridge.

The dataset's canonical harmony convention is the DCML feature decomposition
(``numeral / form / figbass / changes / relativeroot``) — see the spec at
github.com/DCMLab/standards. We *conform* to that notation; we do not copy any
DCML data, which keeps the generated dataset cleanly CC-BY-4.0.

music21 is the engine. Its figure strings match DCML almost exactly for the
vocabulary we generate; the one divergence is the half-diminished glyph
(DCML ``%`` vs music21 ``ø``). All pitch reasoning goes through music21 so the
verification gate (``verify.py``) can cross-check labels against chord symbols.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from music21 import chord, harmony, key, roman

# DCML form glyph -> music21 form glyph. Only '%' differs.
_FORM_DCML_TO_M21 = {"": "", "o": "o", "+": "+", "%": "ø", "M": "M"}
VALID_FORMS = frozenset(_FORM_DCML_TO_M21)
VALID_FIGBASS = frozenset({"", "6", "64", "7", "65", "43", "2"})


@dataclass(frozen=True)
class Analysis:
    """One chord's functional analysis in the DCML feature decomposition.

    ``numeral`` carries triad quality in its case (upper = major third, lower =
    minor third) and may carry an accidental prefix (e.g. ``bII``, ``#iv``).
    """

    numeral: str
    form: str = ""
    figbass: str = ""
    changes: str = ""
    relativeroot: Optional[str] = None

    def __post_init__(self) -> None:
        if self.form not in VALID_FORMS:
            raise ValueError(f"invalid DCML form {self.form!r}")
        if self.figbass not in VALID_FIGBASS:
            raise ValueError(f"invalid figbass {self.figbass!r}")

    def dcml_label(self) -> str:
        """The canonical DCML label string, e.g. ``ii7``, ``IM7``, ``ii%65``, ``V7/V``."""
        base = f"{self.numeral}{self.form}{self.figbass}{self.changes}"
        return f"{base}/{self.relativeroot}" if self.relativeroot else base

    def music21_figure(self) -> str:
        """The equivalent music21 RomanNumeral figure (``%`` -> ``ø``)."""
        base = f"{self.numeral}{_FORM_DCML_TO_M21[self.form]}{self.figbass}{self.changes}"
        return f"{base}/{self.relativeroot}" if self.relativeroot else base

    def to_dict(self) -> dict:
        return {
            "numeral": self.numeral,
            "form": self.form,
            "figbass": self.figbass,
            "changes": self.changes,
            "relativeroot": self.relativeroot,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Analysis":
        return cls(
            numeral=d["numeral"],
            form=d.get("form", ""),
            figbass=d.get("figbass", ""),
            changes=d.get("changes", ""),
            relativeroot=d.get("relativeroot"),
        )

    @classmethod
    def parse(cls, spec: str) -> "Analysis":
        """Parse a compact DCML spec, e.g. ``ii7``, ``IM7``, ``iio6``, ``ii%65``, ``V7/V``."""
        m = _SPEC_RE.match(spec)
        if not m:
            raise ValueError(f"bad chord spec {spec!r}")
        numeral, form, figbass, rel = m.groups()
        return cls(numeral=numeral, form=form or "", figbass=figbass or "", relativeroot=rel)


# accidentals + roman numeral, optional form glyph, optional figbass, optional /relativeroot
_SPEC_RE = re.compile(r"^([b#]*[iIvV]+)([o+%M]?)(\d*)(?:/(.+))?$")


# ---------------------------------------------------------------------------
# music21 bridge. Cached because RomanNumeral / ChordSymbol construction is the
# hot path when transposing hundreds of templates across 24 keys.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def _roman(figure: str, key_name: str) -> roman.RomanNumeral:
    return roman.RomanNumeral(figure, key.Key(key_name))


@lru_cache(maxsize=None)
def _chord_symbol(symbol: str) -> harmony.ChordSymbol:
    return harmony.ChordSymbol(symbol)


def pitch_classes_from_figure(figure: str, key_obj: key.Key) -> frozenset[int]:
    rn = _roman(figure, key_obj.tonicPitchNameWithCase)
    return frozenset(p.pitchClass for p in rn.pitches)


def bass_pc_from_figure(figure: str, key_obj: key.Key) -> int:
    rn = _roman(figure, key_obj.tonicPitchNameWithCase)
    return rn.bass().pitchClass


def pitch_classes_from_symbol(symbol: str) -> frozenset[int]:
    cs = _chord_symbol(symbol)
    return frozenset(p.pitchClass for p in cs.pitches)


def bass_pc_from_symbol(symbol: str) -> int:
    return _chord_symbol(symbol).bass().pitchClass


def spelled_notes_from_figure(figure: str, key_obj: key.Key) -> list[str]:
    """Voiced, bass-first spelled notes, e.g. ``['D4','F4','A4','C5']`` (flats as 'b').

    Enharmonic spelling is preserved (``Cb``, ``E#`` in remote keys) — that is part
    of notation reading. The bass is first, so inversion is recoverable.
    """
    rn = _roman(figure, key_obj.tonicPitchNameWithCase)
    return [p.nameWithOctave.replace("-", "b") for p in rn.pitches]


def bass_first_pcs_from_figure(figure: str, key_obj: key.Key) -> list[int]:
    """Pitch classes in bass-first order, de-duplicated (spelling stripped).

    Order preserves the bass first so inversion stays recoverable, while the
    integers carry no enharmonic hint — the most abstract input tier.
    """
    seen: list[int] = []
    rn = _roman(figure, key_obj.tonicPitchNameWithCase)
    for p in rn.pitches:
        if p.pitchClass not in seen:
            seen.append(p.pitchClass)
    return seen


def chord_symbol_from_figure(figure: str, key_obj: key.Key) -> str:
    """Render a Roman numeral (in a key) to a lead-sheet chord symbol string.

    Uses music21's ``chordSymbolFigureFromChord``. Returns the string as-is;
    unidentifiable chords come back as a sentinel that the verify gate rejects.
    """
    rn = _roman(figure, key_obj.tonicPitchNameWithCase)
    return harmony.chordSymbolFigureFromChord(chord.Chord(rn.pitches))


# Conventional key spellings: one per pitch class, avoiding needless double
# accidentals so generated chord symbols stay clean.
MAJOR_KEYS = ["C", "D-", "D", "E-", "E", "F", "F#", "G", "A-", "A", "B-", "B"]
MINOR_KEYS = ["c", "c#", "d", "e-", "e", "f", "f#", "g", "g#", "a", "b-", "b"]
