# Rameau evaluation protocol

Gold labels are deterministic and machine-verified, so scoring is **exact
match** — no LLM judge, no partial credit beyond the metrics defined below.

## Protocol

- **Split:** `test` (leakage-free by construction: no progression shape in
  `test` appears in `train`/`validation` in any key or any task framing).
- **Prompts:** zero-shot, versioned in `prompts.py` (`PROMPT_VERSION`).
  Scores are comparable only at equal prompt versions.
- **Decoding:** temperature 0. `run_model.py` defaults to this.

## Running

```bash
# any OpenAI-compatible endpoint (ollama, vLLM, LM Studio, OpenAI, OpenRouter)
python eval/run_model.py --config notes_to_rn --model <model> --out preds.jsonl
python eval/score.py preds.jsonl --config notes_to_rn --split test
```

Both scripts are stdlib-only. Predictions are JSONL rows carrying
`shape_id` + `key` (joined against gold) and a `prediction` string.

## Parsing (lenient wrapper, strict answer)

Before comparison the scorer:

- strips markdown code fences and surrounding prose (the answer is taken from
  the **last** matching lines of the response);
- maps unicode music symbols to the dataset's ASCII conventions
  (`♭→b`, `♯→#`, `°→o`, `ø→%`, superscript digits → digits);
- drops separator tokens between numerals (`–`, `|`, `,`, `·`, `->`).

It does **not** forgive wrong case (`i64` ≠ `I64` — minor vs major tonic is
the answer), wrong figures, or missing chords.

## Metrics

| config | metrics |
|---|---|
| `*_to_rn` | `exact` (labels **and** cadence correct — headline), `labels_exact`, `chord_acc` (positional), `cadence_acc`, `parse_failures` |
| `key_id` | `exact` (headline), `tonic_acc`, `mode_acc`, `parse_failures` |

A record whose response cannot be parsed at all counts as wrong (and is
reported in `parse_failures` so prompt-format problems are visible rather
than silently penalized).
