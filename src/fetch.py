"""Run every enabled source, tolerate individual failures, dedupe."""
from __future__ import annotations

import importlib
import re
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

    # pass 1: dedupe by stable id (same URL on multiple boards)
    seen: dict[str, Job] = {}
    for j in all_jobs:
        if j.id not in seen:
            seen[j.id] = j

    # pass 2: 跨源去重 —— 同一岗位在官网和 LinkedIn/JSearch 上 URL 不同，
    # 按 规范化(公司+职位) 合并，优先保留官网源(ats:/dream:)、其次 JD 更全的，
    # 避免同一岗位被重复展示/重复送去 LLM 打分。
    def _key(j: Job) -> str:
        return re.sub(r"[^a-z0-9]+", "", f"{j.company}{j.title}".lower())[:100]

    def _pref(j: Job) -> tuple:
        official = j.source.startswith(("ats:", "dream:"))
        return (official, len(j.description or ""))

    best: dict[str, Job] = {}
    for j in seen.values():
        k = _key(j)
        if not k:
            best[j.id] = j
            continue
        cur = best.get(k)
        if cur is None or _pref(j) > _pref(cur):
            best[k] = j
    deduped = list(best.values())
    print(f"  total {len(all_jobs)} -> {len(seen)} by url -> {len(deduped)} after cross-source dedupe",
          file=sys.stderr)
    return deduped
