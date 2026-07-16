"""Tiny JSON persistence for cross-day dedupe + last-run cache.

State is namespaced per profile so each career direction (ai-governance,
internal-audit, ai-risk) keeps its own dedupe history and last run.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

SEEN_TTL = 45 * 86400  # forget jobs after ~45 days so the file stays small


def _ns_dir(ns: str) -> Path:
    d = DATA / (ns or "default")
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_seen(ns: str = "default") -> dict[str, float]:
    p = _ns_dir(ns) / "seen.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def save_seen(seen: dict[str, float], ns: str = "default") -> None:
    now = time.time()
    fresh = {k: v for k, v in seen.items() if now - v < SEEN_TTL}
    (_ns_dir(ns) / "seen.json").write_text(json.dumps(fresh))


def save_last_run(jobs: list[dict], ns: str = "default") -> None:
    (_ns_dir(ns) / "last_run.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2))


def load_last_run(ns: str = "default") -> list[dict]:
    p = _ns_dir(ns) / "last_run.json"
    if p.exists():
        return json.loads(p.read_text())
    return []
