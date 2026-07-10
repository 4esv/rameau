"""A probabilistic functional-harmony grammar.

Rather than a fixed list of textbook progressions, this assembles phrases from
functional zones — opening (tonic) -> predominant -> dominant -> cadence — with
weighted choices at each step, plus sevenths, inversions, cadential 6-4s, and
secondary dominants. It is a Markov-style generative grammar constrained to
common-practice syntax, so every phrase is musically shaped, cadence-terminated
(key-pinning), and — by construction — labelled correctly.

All chord specs are drawn from a set pre-verified against the gold gate, so the
grammar never emits a chord whose Roman-numeral label disagrees with its pitches.
Deterministic under a seed.
"""
from __future__ import annotations

import random
from typing import Optional

from .vocabulary import Analysis

# Each option is (list-of-specs, weight). Specs are compact DCML labels parsed by
# Analysis.parse. An empty predominant list yields direct I-V-I motion.
_CONFIG = {
    "major": {
        "tonic": "I",
        "submediant": "vi",
        "openings": [
            (["I"], 6), (["I", "I6"], 1), (["I", "vi"], 2),
            (["I", "iii", "vi"], 1), (["I", "V6", "I"], 1), (["I6"], 1),
        ],
        "predominants": [
            ([], 2), (["IV"], 4), (["ii"], 3), (["ii7"], 3), (["ii6"], 2), (["ii65"], 2),
            (["IV", "ii6"], 1), (["vi", "ii7"], 1), (["vi", "IV"], 1), (["I6", "IV"], 1),
            (["V7/V"], 1), (["V7/ii", "ii7"], 1), (["V7/IV", "IV"], 1), (["V7/vi", "vi", "ii7"], 1),
        ],
        "dominants": [
            (["V"], 2), (["V7"], 4), (["V65"], 1), (["I64", "V7"], 2), (["I64", "V"], 1),
            (["viio6", "V7"], 1), (["V7/V", "V7"], 1),
        ],
        # half cadences end on a V *triad*; deceptive resolutions need the
        # dominant in root position (see cadence.py) — hence the separate lists.
        "dominants_half": [(["V"], 4), (["I64", "V"], 2), (["V7/V", "V"], 1)],
        "dominants_deceptive": [(["V7"], 4), (["V"], 2), (["I64", "V7"], 2), (["viio6", "V7"], 1)],
        "plagal_predominants": [(["IV"], 3), (["ii6", "IV"], 1), (["I6", "IV"], 1)],
        "resolutions": [(["I"], 6), (["I6"], 1)],
    },
    "minor": {
        "tonic": "i",
        "submediant": "VI",
        "openings": [
            (["i"], 6), (["i", "i6"], 1), (["i", "VI"], 2), (["i", "III"], 1), (["i6"], 1),
        ],
        "predominants": [
            ([], 2), (["iv"], 4), (["iio6"], 3), (["ii%7"], 2), (["iv6"], 2),
            (["VI", "iv"], 1), (["iv", "iio6"], 1), (["III", "iv"], 1),
            (["V7/V"], 1), (["V7/iv", "iv"], 1), (["V7/VI", "VI", "iio6"], 1),
        ],
        "dominants": [
            (["V"], 2), (["V7"], 4), (["V65"], 1), (["i64", "V7"], 2), (["i64", "V"], 1),
            (["viio6", "V7"], 1), (["V7/V", "V7"], 1),
        ],
        "dominants_half": [(["V"], 4), (["i64", "V"], 2), (["V7/V", "V"], 1)],
        "dominants_deceptive": [(["V7"], 4), (["V"], 2), (["i64", "V7"], 2), (["viio6", "V7"], 1)],
        "plagal_predominants": [(["iv"], 3), (["iio6", "iv"], 1), (["VI", "iv"], 1)],
        "resolutions": [(["i"], 6), (["i6"], 1)],
    },
}

_KINDS = [("authentic", 5), ("half", 2), ("deceptive", 2), ("plagal", 1)]


def _pick(rng: random.Random, options: list[tuple[list, int]]) -> list:
    seqs = [o for o, _ in options]
    weights = [w for _, w in options]
    return list(rng.choices(seqs, weights=weights, k=1)[0])


def _assemble(cfg: dict, rng: random.Random) -> list[str]:
    kind = rng.choices([k for k, _ in _KINDS], weights=[w for _, w in _KINDS], k=1)[0]
    specs = _pick(rng, cfg["openings"])
    if kind == "plagal":
        specs += _pick(rng, cfg["plagal_predominants"])
        specs += [cfg["tonic"]]
    else:
        specs += _pick(rng, cfg["predominants"])
        if kind == "half":
            specs += _pick(rng, cfg["dominants_half"])
        elif kind == "deceptive":
            specs += _pick(rng, cfg["dominants_deceptive"])
            specs += [cfg["submediant"]]
        else:
            specs += _pick(rng, cfg["dominants"])
            specs += _pick(rng, cfg["resolutions"])
    return specs


def generate_phrases(mode: str, n: int, seed: int = 0) -> list[list[Analysis]]:
    """Return up to ``n`` distinct, cadence-terminated phrases for the mode."""
    cfg = _CONFIG[mode]
    rng = random.Random(seed)
    out: list[list[Analysis]] = []
    seen: set[tuple[str, ...]] = set()
    cap = max(500, n * 80)
    for _ in range(cap):
        if len(out) >= n:
            break
        specs = _assemble(cfg, rng)
        phrase = [Analysis.parse(s) for s in specs]
        key_ = tuple(a.dcml_label() for a in phrase)
        if key_ in seen:
            continue
        seen.add(key_)
        out.append(phrase)
    return out
