"""Deterministic scorer for Rameau predictions. Stdlib only — no dependencies.

Usage:
    python eval/score.py preds.jsonl --config notes_to_rn --split test
    python eval/score.py preds.jsonl --gold data/notes_to_rn/test.jsonl

Predictions file: JSONL, one object per record, with a "prediction" field.
If every object also carries "shape_id" and "key", records are joined on
(shape_id, key); otherwise predictions are matched to gold by line order.

Parsing is deliberately lenient about *wrapping* (markdown fences, prose
before the answer, unicode music symbols) and deliberately strict about the
*answer itself* (Roman numeral case and figures must match exactly).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# unicode variants models like to emit -> dataset ASCII conventions
_UNICODE = {
    "♭": "b",   # flat sign
    "♯": "#",   # sharp sign
    "°": "o",   # degree (diminished)
    "ø": "%",   # slashed o (half-diminished)
    "∅": "%",   # empty set, occasionally used for half-diminished
    "–": "-", "—": "-",  # dashes
    "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
    "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
}
_SEPARATORS = {"-", "|", ",", ";", "·", "->", "→"}
_CADENCE_RE = re.compile(r"cadence\s*[:=]\s*([A-Za-z]+)", re.IGNORECASE)
_KEY_RE = re.compile(r"([A-G](?:b{1,2}|#{1,2})?)[\s-]+(major|minor)", re.IGNORECASE)
_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*$")


def normalize(text: str) -> str:
    for k, v in _UNICODE.items():
        text = text.replace(k, v)
    lines = [ln for ln in text.splitlines() if not _FENCE_RE.match(ln.strip())]
    return "\n".join(lines).strip()


def parse_rn(text: str) -> tuple[list[str] | None, str | None]:
    """Extract (labels, cadence) from a model response."""
    text = normalize(text)
    lines = [ln.strip().strip("`") for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None, None

    cadence = None
    labels_line = None
    cad_idx = None
    for i in range(len(lines) - 1, -1, -1):
        m = _CADENCE_RE.search(lines[i])
        if m:
            cadence = m.group(1).upper().rstrip(".")
            cad_idx = i
            break

    if cad_idx is not None:
        before = lines[cad_idx][: _CADENCE_RE.search(lines[cad_idx]).start()].strip()
        if before:  # single-line answer: "ii7 V7 I cadence: PAC"
            labels_line = before
        else:
            for j in range(cad_idx - 1, -1, -1):
                if lines[j]:
                    labels_line = lines[j]
                    break
    else:
        labels_line = lines[-1]

    if not labels_line:
        return None, cadence

    tokens = []
    for tok in labels_line.split():
        tok = tok.strip("`,.;")
        if not tok or tok in _SEPARATORS:
            continue
        tokens.append(tok)
    return (tokens or None), cadence


def parse_key(text: str) -> str | None:
    """Extract 'Tonic mode' from a model response (last match wins)."""
    text = normalize(text)
    last = None
    for m in _KEY_RE.finditer(text):
        tonic, mode = m.group(1), m.group(2)
        last = f"{tonic[0].upper()}{tonic[1:].lower()} {mode.lower()}"
    return last


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(ln) for ln in fh if ln.strip()]


def join(gold: list[dict], preds: list[dict]) -> list[tuple[dict, dict]]:
    if preds and all("shape_id" in p and "key" in p for p in preds):
        by_id = {(p["shape_id"], p["key"]): p for p in preds}
        pairs = [(g, by_id[(g["shape_id"], g["key"])]) for g in gold
                 if (g["shape_id"], g["key"]) in by_id]
        if len(pairs) < len(preds):
            print(f"warning: {len(preds) - len(pairs)} predictions matched no gold record",
                  file=sys.stderr)
        return pairs
    if len(preds) != len(gold):
        raise SystemExit(
            f"positional join needs equal counts (gold {len(gold)}, preds {len(preds)}); "
            "or include shape_id+key in each prediction"
        )
    return list(zip(gold, preds))


def score_rn(pairs: list[tuple[dict, dict]]) -> dict:
    n = len(pairs)
    exact = labels_exact = cad_ok = parse_fail = 0
    chord_hits = chord_total = 0
    for g, p in pairs:
        labels, cadence = parse_rn(p.get("prediction") or "")
        if labels is None:
            parse_fail += 1
        gl = g["labels"]
        l_ok = labels == gl
        c_ok = cadence == g["cadence"]  # both None counts as correct
        labels_exact += l_ok
        cad_ok += c_ok
        exact += l_ok and c_ok
        chord_total += len(gl)
        if labels:
            chord_hits += sum(a == b for a, b in zip(labels, gl))
    return {
        "n": n,
        "exact": round(exact / n, 4),
        "labels_exact": round(labels_exact / n, 4),
        "chord_acc": round(chord_hits / chord_total, 4),
        "cadence_acc": round(cad_ok / n, 4),
        "parse_failures": parse_fail,
    }


def score_key(pairs: list[tuple[dict, dict]]) -> dict:
    n = len(pairs)
    exact = tonic_ok = mode_ok = parse_fail = 0
    for g, p in pairs:
        pred = parse_key(p.get("prediction") or "")
        if pred is None:
            parse_fail += 1
            continue
        gt, gm = g["target"].rsplit(" ", 1)
        pt, pm = pred.rsplit(" ", 1)
        exact += pred == g["target"]
        tonic_ok += pt == gt
        mode_ok += pm == gm
    return {
        "n": n,
        "exact": round(exact / n, 4),
        "tonic_acc": round(tonic_ok / n, 4),
        "mode_acc": round(mode_ok / n, 4),
        "parse_failures": parse_fail,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("predictions", type=Path)
    ap.add_argument("--config", choices=["symbol_to_rn", "notes_to_rn", "pcset_to_rn", "key_id"])
    ap.add_argument("--split", default="test", choices=["train", "validation", "test"])
    ap.add_argument("--gold", type=Path, help="explicit gold JSONL (overrides --config/--split)")
    args = ap.parse_args()

    if args.gold:
        gold_path = args.gold
        config = args.config or gold_path.parent.name
    elif args.config:
        gold_path = REPO_ROOT / "data" / args.config / f"{args.split}.jsonl"
        config = args.config
    else:
        raise SystemExit("need --config or --gold")

    gold = load_jsonl(gold_path)
    preds = load_jsonl(args.predictions)
    pairs = join(gold, preds)
    metrics = score_key(pairs) if config == "key_id" else score_rn(pairs)
    print(json.dumps({"config": config, "split": args.split, **metrics}, indent=2))


if __name__ == "__main__":
    main()
