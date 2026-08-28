"""Push the dataset repo to the Hub: uv run python scripts/push_to_hub.py

Publishes everything needed to load, audit, and reproduce the dataset.
BRIEF.md (internal seed notes) stays local.
"""
from __future__ import annotations

from pathlib import Path

from huggingface_hub import HfApi

REPO_ID = "4esv/rameau"
REPO_ROOT = Path(__file__).resolve().parents[1]

IGNORE = [
    "BRIEF.md",
    ".git*",
    ".venv/**",
    "**/__pycache__/**",
    ".pytest_cache/**",
    ".ruff_cache/**",
    ".DS_Store",
]


def main() -> None:
    api = HfApi()
    user = api.whoami()["name"]
    assert user == REPO_ID.split("/")[0], f"logged in as {user!r}, expected {REPO_ID}"
    api.create_repo(REPO_ID, repo_type="dataset", exist_ok=True)
    info = api.upload_folder(
        repo_id=REPO_ID,
        repo_type="dataset",
        folder_path=REPO_ROOT,
        ignore_patterns=IGNORE,
        commit_message="v1: 21,940 records, 4 configs, verified gold, eval harness",
    )
    print(f"pushed: https://huggingface.co/datasets/{REPO_ID}\ncommit: {info.oid}")


if __name__ == "__main__":
    main()
