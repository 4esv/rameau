"""Versioned zero-shot prompts for the Roman Numeral Harmony Benchmark.

Bump PROMPT_VERSION whenever any prompt text changes; scores are only
comparable at equal prompt versions.
"""
from __future__ import annotations

PROMPT_VERSION = "1"

_RN_FORMAT = """\
Respond with EXACTLY this format and nothing else:
<Roman numerals separated by single spaces>
cadence: <PAC|IAC|HC|DC|PC>
If the phrase does not end with a cadence, output only the Roman-numeral line.
Use DCML-style Roman numerals as in these examples: I, ii7, V65, viio6, IM7, V7/vi, ii%7, i64.
(%7 = half-diminished seventh, o = diminished, M7 = major seventh.)"""

_TASK_LINE = {
    "symbol_to_rn": (
        "Analyze the chord progression in the given key and provide the "
        "Roman-numeral analysis of every chord, in order."
    ),
    "notes_to_rn": (
        "Each chord is given as spelled notes, bass note first. Analyze the "
        "progression in the given key and provide the Roman-numeral analysis "
        "of every chord, in order."
    ),
    "pcset_to_rn": (
        "Each chord is given as a list of pitch classes (0 = C, 1 = C#/Db, ... "
        "11 = B), bass pitch class first. Analyze the progression in the given "
        "key and provide the Roman-numeral analysis of every chord, in order."
    ),
}

_KEY_ID_PROMPT = """\
You are analyzing tonal harmony in the common-practice style.
Each chord is given as spelled notes, bass note first. Identify the key of the phrase.
Respond with EXACTLY the key and nothing else, in the form: <Tonic> <major|minor>
Examples: C major / Eb major / F# minor

{input}"""

_RN_PROMPT = """\
You are analyzing tonal harmony in the common-practice style.
{task_line}
{format_block}

{input}"""


def build_prompt(config: str, input_text: str) -> str:
    if config == "key_id":
        return _KEY_ID_PROMPT.format(input=input_text)
    if config in _TASK_LINE:
        return _RN_PROMPT.format(
            task_line=_TASK_LINE[config], format_block=_RN_FORMAT, input=input_text
        )
    raise ValueError(f"unknown config {config!r}")
