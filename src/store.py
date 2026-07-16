"""Tiny JSON persistence for cross-day dedupe + last-run cache."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
SEEN = DATA / "seen.json"
LAST = DATA / "last_run.json"

SEEN_TTL = 45 * 86400  # forget jobs after ~45 days so the file stays small


def load_seen() -> dict[str, float]:
    if SEEN.exists():
        try:
            return json.loads(SEEN.read_text())
        except Exception:
            return {}
    return {}


def save_seen(seen: dict[str, float]) -> None:
    now = time.time()
    fresh = {k: v for k, v in seen.items() if now - v < SEEN_TTL}
    DATA.mkdir(exist_ok=True)
    SEEN.write_text(json.dumps(fresh))


def save_last_run(jobs: list[dict]) -> None:
    DATA.mkdir(exist_ok=True)
    LAST.write_text(json.dumps(jobs, ensure_ascii=False, indent=2))


def load_last_run() -> list[dict]:
    if LAST.exists():
        return json.loads(LAST.read_text())
    return []
