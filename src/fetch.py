"""Run every enabled source, tolerate individual failures, dedupe."""
from __future__ import annotations

import importlib
import sys

from .sources.base import Job

# config key -> module name under src.sources
REGISTRY = {
    "remoteok": "remoteok",
    "remotive": "remotive",
    "arbeitnow": "arbeitnow",
    "weworkremotely": "weworkremotely",
    "jobicy": "jobicy",
    "hackernews": "hackernews",
    "themuse": "themuse",
    "adzuna": "adzuna",
    "jsearch": "jsearch",
    "ats_boards": "ats_boards",   # 公司官网直连（无需 key），见 career/ats_companies.yaml
}


def fetch_all(cfg: dict) -> list[Job]:
    enabled = cfg.get("sources", {}) or {}
    all_jobs: list[Job] = []
    for key, on in enabled.items():
        if not on or key not in REGISTRY:
            continue
        mod = importlib.import_module(f"src.sources.{REGISTRY[key]}")
        try:
            jobs = mod.fetch(cfg)
            print(f"  [{key}] {len(jobs)} jobs", file=sys.stderr)
            all_jobs.extend(jobs)
        except Exception as e:  # one bad source shouldn't kill the run
            print(f"  [{key}] FAILED: {e}", file=sys.stderr)

    # dedupe by stable id (same job can appear on multiple boards)
    seen: dict[str, Job] = {}
    for j in all_jobs:
        if j.id not in seen:
            seen[j.id] = j
    deduped = list(seen.values())
    print(f"  total {len(all_jobs)} -> {len(deduped)} after dedupe", file=sys.stderr)
    return deduped
