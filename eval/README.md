# Rameau evaluation protocol

Gold is deterministic, so scoring is exact match. No LLM judge.

## Protocol

- Split: `test`. Leakage-free by construction; no shape in test appears in
  train or validation, in any key or framing.
- Prompts: zero-shot, versioned in `prompts.py`. Scores are comparable only at
  equal `PROMPT_VERSION`.
- Decoding: temperature 0. Set `max_tokens` high enough that it never binds.
  A reasoning model that spends its whole budget thinking returns nothing,
  and nothing scores nothing.

## Running

```bash
python eval/run_model.py --config notes_to_rn --model <model> --out preds.jsonl
python eval/score.py preds.jsonl --config notes_to_rn --split test
```

Both scripts are stdlib-only. `run_model.py` speaks to any OpenAI-compatible
endpoint (ollama, vLLM, OpenAI, OpenRouter). Predictions carry `shape_id` and
`key` for joining, plus the model, prompt version, reasoning setting, and
finish reason, so a predictions file documents its own run.

## Parsing

The scorer is lenient about wrapping and strict about the answer. It strips
code fences and surrounding prose (the answer is read from the last matching
lines), maps unicode music symbols to the dataset's ASCII (`b`, `#`, `o`, `%`),
and drops separator tokens between numerals. It does not forgive wrong case:
`i64` is not `I64`, and minor versus major is usually the question.

Unparseable responses count as wrong and are tallied in `parse_failures`, so
format problems stay visible instead of hiding in the accuracy.

## Metrics

| config | metrics |
|---|---|
| `*_to_rn` | `exact` (labels and cadence both correct), `labels_exact`, `chord_acc` (positional), `cadence_acc`, `parse_failures` |
| `key_id` | `exact`, `tonic_acc`, `mode_acc`, `parse_failures` |
