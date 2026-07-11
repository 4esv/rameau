"""Query a model on a Rameau config and write predictions for score.py.

Works against any OpenAI-compatible chat-completions endpoint (ollama, vLLM,
LM Studio, OpenAI, OpenRouter, ...). Stdlib only.

Usage:
    python eval/run_model.py --config notes_to_rn --model qwen2.5:7b \\
        --base-url http://localhost:11434/v1 --out preds.jsonl
    python eval/score.py preds.jsonl --config notes_to_rn --split test

Gold records are read from the repo's data/ directory when present, so this
runs from a fresh `git clone` of the dataset repo with no extra dependencies.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompts import PROMPT_VERSION, build_prompt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
RETRIES = 3


def load_records(config: str, split: str, data_dir: Path) -> list[dict]:
    path = data_dir / config / f"{split}.jsonl"
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            return [json.loads(ln) for ln in fh if ln.strip()]
    try:  # fall back to the Hub if datasets is installed
        from datasets import load_dataset
    except ImportError:
        raise SystemExit(f"{path} not found and `datasets` not installed")
    return list(load_dataset("4esv/rameau", config, split=split))


def complete(base_url: str, api_key: str, model: str, prompt: str,
             temperature: float, max_tokens: int) -> tuple[str, str | None]:
    """Return (content, finish_reason). finish_reason 'length' with empty
    content usually means a thinking model spent max_tokens on reasoning."""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
    )
    last_err: Exception | None = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.load(resp)
            choice = data["choices"][0]
            return choice["message"]["content"], choice.get("finish_reason")
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
            last_err = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"request failed after {RETRIES} attempts: {last_err}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True,
                    choices=["symbol_to_rn", "notes_to_rn", "pcset_to_rn", "key_id"])
    ap.add_argument("--split", default="test", choices=["train", "validation", "test"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL",
                                                         "http://localhost:11434/v1"))
    ap.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", "none"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    ap.add_argument("--limit", type=int, help="evaluate only the first N records")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--prompt-suffix", default="",
                    help="appended to every prompt, e.g. ' /no_think' for Qwen3 "
                         "on ollama; recorded in the output rows")
    args = ap.parse_args()

    records = load_records(args.config, args.split, args.data_dir)
    if args.limit:
        records = records[: args.limit]

    def run_one(rec: dict) -> dict:
        prompt = build_prompt(args.config, rec["input"]) + args.prompt_suffix
        finish = err = None
        try:
            pred, finish = complete(args.base_url, args.api_key, args.model, prompt,
                                    args.temperature, args.max_tokens)
        except RuntimeError as exc:
            pred, err = "", str(exc)
        return {
            "shape_id": rec["shape_id"],
            "key": rec["key"],
            "prediction": pred,
            "finish_reason": finish,
            **({"error": err} if err else {}),
            **({"prompt_suffix": args.prompt_suffix} if args.prompt_suffix else {}),
            "model": args.model,
            "prompt_version": PROMPT_VERSION,
        }

    done = errors = 0
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool, \
            open(args.out, "w", encoding="utf-8") as fh:
        for row in pool.map(run_one, records):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            done += 1
            errors += "error" in row
            if done % 50 == 0:
                print(f"{done}/{len(records)}", file=sys.stderr)
    print(f"wrote {done} predictions to {args.out}"
          + (f" ({errors} request errors)" if errors else ""), file=sys.stderr)


if __name__ == "__main__":
    main()
