"""Assemble the dataset on disk: one config per task, three splits each, plus a
draft dataset card and a verification report.

Run: ``uv run python -m harmony_dataset.export``. Nothing here pushes to the Hub.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from . import tasks
from .generator import GenResult, generate

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
SPLITS = ("train", "validation", "test")
DEFAULT_CONFIG = "notes_to_rn"

TASK_BLURB = {
    "symbol_to_rn": "key + chord symbols -> Roman numerals + cadence (easy: chord quality is given)",
    "notes_to_rn": "key + spelled notes -> Roman numerals + cadence (must read each chord)",
    "pcset_to_rn": "key + bass-first pitch-class lists -> Roman numerals + cadence (no spelling)",
    "key_id": "spelled notes, no key -> identify the key (only key-unambiguous phrases)",
}
CADENCE_GLOSS = {
    "PAC": "perfect authentic", "IAC": "imperfect authentic", "HC": "half",
    "DC": "deceptive", "PC": "plagal",
}


def bucket(res: GenResult) -> dict[tuple[str, str], list[dict]]:
    out: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in res.records:
        out[(r.data["task"], r.split)].append(r.data)
    # stable order within each file
    for recs in out.values():
        recs.sort(key=lambda d: (d["shape_id"], d["key"]))
    return out


def write_jsonl(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for d in records:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")


def _configs_yaml() -> str:
    lines = ["configs:"]
    for task in tasks.TASKS:
        lines.append(f"  - config_name: {task}")
        if task == DEFAULT_CONFIG:
            lines.append("    default: true")
        lines.append("    data_files:")
        for split in SPLITS:
            lines.append(f"      - split: {split}")
            lines.append(f"        path: data/{task}/{split}.jsonl")
    return "\n".join(lines)


def render_card(res: GenResult, buckets: dict) -> str:
    total = len(res.records)
    per_task = Counter(r.data["task"] for r in res.records)
    per_split = Counter(r.split for r in res.records)
    size_cat = "10K<n<100K" if 10_000 <= total < 100_000 else "1K<n<10K" if total >= 1_000 else "n<1K"
    task_rows = "\n".join(
        f"| `{t}` | {TASK_BLURB[t]} | {per_task[t]:,} |" for t in tasks.TASKS
    )
    return f"""---
pretty_name: "Roman Numeral Harmony Benchmark: Functional Harmony from Notation"
license: cc-by-4.0
language:
  - en
task_categories:
  - text-generation
tags:
  - music
  - music-theory
  - functional-harmony
  - roman-numeral-analysis
  - chord-progression
  - cadence
  - key-detection
  - benchmark
  - evaluation
  - reasoning
  - synthetic
  - mir
  - symbolic-music
size_categories:
  - {size_cat}
annotations_creators:
  - machine-generated
source_datasets:
  - original
{_configs_yaml()}
---

# Roman Numeral Harmony Benchmark

A text-to-text dataset and benchmark for functional harmony: Roman-numeral
analysis, cadence classification, and key identification. A probabilistic
common-practice grammar generates the progressions; four task framings hide
the answer to increasing degrees. Chord-symbol lookup stops working after the
first one.

```
symbol_to_rn  key: C major / progression: Dm7 G7 Cmaj7   ->  ii7 V7 IM7 / cadence: PAC
notes_to_rn   key: C major / notes: D4 F4 A4 C5 | ...     ->  ii7 V7 IM7 / cadence: PAC
pcset_to_rn   key: C major / pitch classes: [2 5 9 0]|... ->  ii7 V7 IM7 / cadence: PAC
key_id        notes: D4 F4 A4 C5 | G3 B3 D4 F4 | ...      ->  C major
```

## Configs (tasks)

Load one with `load_dataset("4esv/roman-numeral-harmony-benchmark", "<config>")`. Default: `{DEFAULT_CONFIG}`.

| config | task | rows |
|---|---|---|
{task_rows}
| | **total** | **{total:,}** |

## Gold labels

Nothing is hand-annotated. The grammar (tonic -> predominant -> dominant ->
cadence, with sevenths, inversions, cadential 6-4s and secondary dominants)
generates each progression together with its intended analysis. Every chord is
then derived two independent ways with [`music21`](https://web.mit.edu/music21/):
the Roman-numeral figure through the roman engine, and the printed chord symbol
through the chord-symbol parser. An item is kept only if both agree on
pitch-class set and bass.
This release: {res.attempted_chords - len(res.failures):,} of {res.attempted_chords:,} chords agree. See `VERIFY.md`.

Built from {res.shapes} progression shapes (key-independent), transposed across
keys. All content is synthetic; no third-party corpus is redistributed.

## Label convention

Roman numerals follow the feature decomposition of the
[DCML harmony standard](https://github.com/DCMLab/standards)
(`numeral` / `form` / `figbass` / `changes` / `relativeroot`).
We follow the notation and copy no DCML data. Major-seventh tonic is `IM7`;
secondary dominants use `/` (e.g. `V7/vi`).
Cadence codes: {", ".join(f"`{k}` {v}" for k, v in CADENCE_GLOSS.items())}.

## Fields

Common to every config: `input`, `target`, `key`, `mode`, `labels`, `cadence`,
`analysis` (per-chord DCML features), `source` (`grammar`/`curated`/`single`),
`category`, `shape_id`. Plus the input representation for the config: `chords`
(symbols), `notes` (spelled, bass-first), or `pitch_classes` (bass-first).

Accidentals are written the standard way (`Bb`, `F#`, `Cb`). music21 users:
its parsers want `-` for flats, so convert `b -> -` in note and root names
before calling `ChordSymbol` or `Pitch`.

## Splits

The atomic unit is a shape, a key-independent Roman-numeral sequence. A shape
hashes to exactly one split, so none of its transpositions or task framings
crosses splits. The test split doubles as the benchmark. Rows:
train {per_split['train']:,} / validation {per_split['validation']:,} / test {per_split['test']:,}.

## Known limitations

- The distribution is synthetic. Grammar output, not repertoire; chord
  statistics are not naturalistic.
- PAC vs IAC is decided by inversion, since there is no notated soprano.
  Cadence rules are strict: an HC ends on a root-position V triad (a terminal
  V7 is not labelled), and a DC requires a root-position dominant
  (`V65 -> vi` does not count).
- key_id keeps only cadence-terminated progressions of three or more chords
  whose notes contain scale degree 4 and the leading tone, so the key is
  uniquely determined. Without the gate, gold keys are contestable: `I V7/V V`
  in C is note-identical to `IV V7 I` in G, and the G reading is arguably
  stronger. Such phrases are excluded.
- Harmony only: no voice leading, melody, or rhythm. No modal mixture,
  Neapolitans, or augmented sixths yet.

## Evaluation

Gold is deterministic, so scoring is exact match. No LLM judge. The harness in
`eval/` is stdlib-only and works against any OpenAI-compatible endpoint:

```bash
python eval/run_model.py --config notes_to_rn --model <model> --out preds.jsonl
python eval/score.py preds.jsonl --config notes_to_rn --split test
```

Metrics for the RN configs: `exact` (numerals and cadence both correct),
`labels_exact`, `chord_acc`, `cadence_acc`. For `key_id`: `exact`, `tonic_acc`,
`mode_acc`. Prompts are versioned in `eval/prompts.py`; parsing rules are in
`eval/README.md`.

## Results

Full test split, zero-shot, temperature 0, prompt v1, run 2026-07-11 via
OpenRouter. Cells are exact match, with per-chord accuracy in parentheses.
Raw predictions and per-run metadata are in `results/`.

| model | symbol_to_rn | notes_to_rn | pcset_to_rn | key_id |
|---|---|---|---|---|
| gpt-oss-120b (reasoning low) | 0.256 (0.885) | 0.155 (0.778) | 0.146 (0.724) | 0.778 |
| Claude Sonnet 5 | 0.220 (0.863) | 0.066 (0.688) | 0.157 (0.732) | 0.823 |
| Qwen3-235B-A22B-Instruct | 0.193 (0.739) | 0.016 (0.380) | 0.002 (0.163) | 0.719 |
| DeepSeek-V3.2 | 0.151 (0.634) | 0.005 (0.305) | 0.001 (0.150) | 0.661 |
| Kimi-K2.5 | 0.142 (0.562) | 0.007 (0.399) | 0.009 (0.205) | 0.788 |
| Llama-3.3-70B | 0.037 (0.466) | 0.004 (0.307) | 0.000 (0.194) | 0.471 |

No model saturates the easiest config. Models that do not reason drop toward
zero once the chord symbols disappear; the two that do degrade more slowly.
Claude Sonnet 5 scores higher on pitch classes than on spelled notes, which
suggests spelling rather than harmony is its bottleneck. The table cost about
nine dollars in API credits.

### Reasoning on vs off

Fixed test subsets rerun with reasoning enabled; n in the table. Exact match
on `notes_to_rn`:

| model | n | off | on |
|---|---|---|---|
| Kimi-K2.5 | 150 | 0.000 | 0.740 |
| DeepSeek-V3.2 | 200 | 0.025 | 0.725 |
| Claude Sonnet 5 | 100 | 0.090 | 0.520 |
| gpt-oss-120b (low -> high) | 200 | 0.185 | 0.440 |

The pattern holds on every config; full numbers are in `results/reasoning/`.
With thinking enabled, per-chord accuracy reaches 0.89 to 0.98 on the hidden
configs, so the remaining exact-match gap is mostly cadence and figure errors.
Without thinking the benchmark measures pattern recall; with thinking it
measures multi-step computation. Neither saturates it.

## Reproduce

The full generation pipeline ships in this repo (`src/harmony_dataset/`):

```bash
uv sync && uv run pytest
uv run python -m harmony_dataset.export    # regenerates data/, README, VERIFY.md
```

## Related work

- [MusicTheoryBench](https://huggingface.co/datasets/m-a-p/MusicTheoryBench)
  (ChatMusician, 2024): 372 hand-written multiple-choice questions on broad
  music knowledge. This benchmark is generative and machine-verified.
- [Harmonic Reasoning in LLMs](https://arxiv.org/abs/2409.05521) (Kruspe, 2024):
  synthetic interval, chord, and scale identification. No key context, so
  identification rather than functional analysis.
- [Teaching LLMs Music Theory](https://arxiv.org/abs/2503.22853)
  (Pond & Fujinaga, 2025): one RCM Level 6 exam in four encodings, with
  prompting strategies. This benchmark frames the same progressions in each
  representation, so representation is the only variable.
- Score-based Roman-numeral analysis (Micchi et al., AugmentedNet, AnalysisGNN):
  specialist models trained on NC-licensed annotated corpora. This benchmark targets
  text models and generates its own data, which is what keeps the license CC-BY.

## Licensing

CC-BY-4.0. Content is generated by this repository's pipeline from music theory;
the underlying facts are not copyrightable and no source corpus is redistributed.

## Citation

```
@misc{{rnharmonybench,
  title  = {{Roman Numeral Harmony Benchmark: Functional Harmony from Notation}},
  author = {{Stevens, Axel}},
  year   = {{2026}},
  doi    = {{10.57967/hf/9570}},
  url    = {{https://huggingface.co/datasets/4esv/roman-numeral-harmony-benchmark}},
  note   = {{Synthetic, music21-verified, DCML labels}}
}}
```
"""


def render_verify(res: GenResult) -> str:
    L: list[str] = ["# Verification report\n", "## Gold gate (dual-derivation agreement)\n",
                    "| metric | value |", "|---|---|",
                    f"| distinct shapes | {res.shapes} |",
                    f"| instances (shape x key) | {res.instances} |",
                    f"| instances dropped | {res.dropped_instances} |",
                    f"| chords attempted | {res.attempted_chords} |",
                    f"| chord disagreements | {len(res.failures)} |",
                    f"| **chord agreement rate** | **{res.chord_agreement_rate:.3%}** |",
                    f"| total records | {len(res.records)} |\n"]

    per_source = Counter(r.data["source"] for r in res.records)
    per_cadence = Counter(r.data["cadence"] for r in res.records)
    L += ["## Distribution\n", f"- by source: {dict(per_source)}",
          f"- by cadence: {dict(per_cadence)}\n"]

    if res.failures:
        L += ["## Dropped chords\n", "| shape | key | figure | symbol | reason |", "|---|---|---|---|---|"]
        for f in res.failures[:50]:
            c = f.check
            L.append(f"| {f.shape_id} | {f.key} | `{c.figure}` | `{c.symbol}` | {c.reason} |")
        L.append("")

    # the brief example across all four task framings
    L.append("## Same progression, four framings (brief example in C major)\n")
    brief = [r.data for r in res.records
             if r.data["shape_id"] == _shape_id_of(res, ["ii7", "V7", "IM7"])
             and r.data["key"] == "C major"]
    for d in sorted(brief, key=lambda d: tasks.TASKS.index(d["task"])):
        L.append(f"- **{d['task']}**")
        L.append(f"  - in:  `{d['input'].replace(chr(10), '  //  ')}`")
        L.append(f"  - out: `{d['target'].replace(chr(10), '  //  ')}`")
    L.append("")

    # a spread of grammar phrases (notes_to_rn framing, reference key)
    L.append("## Grammar phrases (notes_to_rn, in C major / A minor)\n")
    shown = 0
    for r in sorted(res.records, key=lambda r: r.data["shape_id"]):
        d = r.data
        if d["task"] != "notes_to_rn" or d["source"] != "grammar":
            continue
        if d["key"] not in ("C major", "A minor"):
            continue
        cad = d["cadence"] or "-"
        L.append(f"- `{d['key']}`  {d['input'].split('notes: ')[1]}")
        L.append(f"  -> `{' '.join(d['labels'])}` ({cad})")
        shown += 1
        if shown >= 12:
            break
    L.append("")
    return "\n".join(L)


def _shape_id_of(res: GenResult, labels: list[str]) -> str:
    for r in res.records:
        if r.data["labels"] == labels:
            return r.data["shape_id"]
    return ""


def main(out_dir: Path = REPO_ROOT) -> GenResult:
    res = generate()
    buckets = bucket(res)
    for (task, split), recs in buckets.items():
        write_jsonl(recs, out_dir / "data" / task / f"{split}.jsonl")
    (out_dir / "README.md").write_text(render_card(res, buckets), encoding="utf-8")
    (out_dir / "VERIFY.md").write_text(render_verify(res), encoding="utf-8")
    print(f"wrote {len(res.records)} records across {len(tasks.TASKS)} configs "
          f"from {res.shapes} shapes; chord agreement {res.chord_agreement_rate:.3%}")
    return res


if __name__ == "__main__":
    main()
