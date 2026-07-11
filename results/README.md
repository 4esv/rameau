# Results

Raw predictions for the table in the dataset card. Full test split, zero-shot,
temperature 0, prompt v1, run 2026-07-11 through OpenRouter. One directory per
model, one JSONL per config; `scores.json` holds every metric.

Each prediction row records the model, prompt version, reasoning setting, and
finish reason, so the files describe their own runs. Reasoning settings:
gpt-oss-120b ran at effort `low` with `max_tokens` 4096 (at 1024 it spent the
budget thinking and answered nothing on 10% of `notes_to_rn`); Claude Sonnet 5,
DeepSeek-V3.2, and Kimi-K2.5 ran with reasoning disabled; Qwen3-235B-Instruct
and Llama-3.3-70B do not reason.

Reproduce a run:

```bash
python eval/run_model.py --config notes_to_rn --split test \
  --model openai/gpt-oss-120b --reasoning low --max-tokens 4096 \
  --base-url https://openrouter.ai/api/v1 --api-key $OPENROUTER_API_KEY \
  --out preds.jsonl
python eval/score.py preds.jsonl --config notes_to_rn --split test
```
