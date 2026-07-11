---
pretty_name: "Rameau: Functional Harmony from Notation (Roman Numerals, Cadence, Key)"
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
  - synthetic
size_categories:
  - 10K<n<100K
annotations_creators:
  - machine-generated
source_datasets:
  - original
configs:
  - config_name: symbol_to_rn
    data_files:
      - split: train
        path: data/symbol_to_rn/train.jsonl
      - split: validation
        path: data/symbol_to_rn/validation.jsonl
      - split: test
        path: data/symbol_to_rn/test.jsonl
  - config_name: notes_to_rn
    default: true
    data_files:
      - split: train
        path: data/notes_to_rn/train.jsonl
      - split: validation
        path: data/notes_to_rn/validation.jsonl
      - split: test
        path: data/notes_to_rn/test.jsonl
  - config_name: pcset_to_rn
    data_files:
      - split: train
        path: data/pcset_to_rn/train.jsonl
      - split: validation
        path: data/pcset_to_rn/validation.jsonl
      - split: test
        path: data/pcset_to_rn/test.jsonl
  - config_name: key_id
    data_files:
      - split: train
        path: data/key_id/train.jsonl
      - split: validation
        path: data/key_id/validation.jsonl
      - split: test
        path: data/key_id/test.jsonl
---

# Rameau: functional harmony from notation

A text-to-text dataset and benchmark for functional harmony: Roman-numeral
analysis, cadence classification, and key identification. A probabilistic
common-practice grammar generates the progressions; four task framings hide
the answer to increasing degrees. Chord-symbol lookup stops working after the
first one.

Named for Jean-Philippe Rameau, whose *Traité de l'harmonie* (1722) started
the discipline.

```
symbol_to_rn  key: C major / progression: Dm7 G7 Cmaj7   ->  ii7 V7 IM7 / cadence: PAC
notes_to_rn   key: C major / notes: D4 F4 A4 C5 | ...     ->  ii7 V7 IM7 / cadence: PAC
pcset_to_rn   key: C major / pitch classes: [2 5 9 0]|... ->  ii7 V7 IM7 / cadence: PAC
key_id        notes: D4 F4 A4 C5 | G3 B3 D4 F4 | ...      ->  C major
```

## Configs (tasks)

Load one with `load_dataset("4esv/rameau", "<config>")`. Default: `notes_to_rn`.

| config | task | rows |
|---|---|---|
| `symbol_to_rn` | key + chord symbols -> Roman numerals + cadence (easy: chord quality is given) | 5715 |
| `notes_to_rn` | key + spelled notes -> Roman numerals + cadence (must read each chord) | 5715 |
| `pcset_to_rn` | key + bass-first pitch-class lists -> Roman numerals + cadence (no spelling) | 5715 |
| `key_id` | spelled notes, no key -> identify the key (only key-unambiguous phrases) | 4795 |
| | **total** | **21940** |

## Gold labels

Nothing is hand-annotated. The grammar (tonic -> predominant -> dominant ->
cadence, with sevenths, inversions, cadential 6-4s and secondary dominants)
generates each progression together with its intended analysis. Every chord is
then derived two independent ways with [`music21`](https://web.mit.edu/music21/):
the Roman-numeral figure through the roman engine, and the printed chord symbol
through the chord-symbol parser. An item is kept only if both agree on
pitch-class set and bass. This release: 27480 of
27480 chords agree. See `VERIFY.md`.

Built from 845 progression shapes (key-independent), transposed across
keys. All content is synthetic; no third-party corpus is redistributed.

## Label convention

Roman numerals follow the [DCML harmony standard](https://github.com/DCMLab/standards)'s
feature decomposition (`numeral` / `form` / `figbass` / `changes` / `relativeroot`).
We follow the notation and copy no DCML data. Major-seventh tonic is `IM7`;
secondary dominants use `/` (e.g. `V7/vi`).
Cadence codes: `PAC` perfect authentic, `IAC` imperfect authentic, `HC` half, `DC` deceptive, `PC` plagal.

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
train 14725 / validation 3571 / test 3644.

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

## Reproduce

The full generation pipeline ships in this repo (`src/harmony_dataset/`):

```bash
uv sync && uv run pytest
uv run python -m harmony_dataset.export    # regenerates data/, README, VERIFY.md
```

## Related work

- [MusicTheoryBench](https://huggingface.co/datasets/m-a-p/MusicTheoryBench)
  (ChatMusician, 2024): 372 hand-written multiple-choice questions on broad
  music knowledge. Rameau is generative and machine-verified.
- [Harmonic Reasoning in LLMs](https://arxiv.org/abs/2409.05521) (Kruspe, 2024):
  synthetic interval, chord, and scale identification. No key context, so
  identification rather than functional analysis.
- [Teaching LLMs Music Theory](https://arxiv.org/abs/2503.22853)
  (Pond & Fujinaga, 2025): one RCM Level 6 exam in four encodings, with
  prompting strategies. Rameau frames the same progressions in each
  representation, so representation is the only variable.
- Score-based Roman-numeral analysis (Micchi et al., AugmentedNet, AnalysisGNN):
  specialist models trained on NC-licensed annotated corpora. Rameau targets
  text models and generates its own data, which is what keeps the license CC-BY.

## Licensing

CC-BY-4.0. Content is generated by this repository's pipeline from music theory;
the underlying facts are not copyrightable and no source corpus is redistributed.

## Citation

```
@misc{rameau,
  title  = {Rameau: Functional Harmony from Notation (Roman Numerals, Cadence, Key)},
  author = {Stevens, Axel},
  year   = {2026},
  url    = {https://huggingface.co/datasets/4esv/rameau},
  note   = {Synthetic, grammar-generated, music21-verified, DCML-convention labels}
}
```
