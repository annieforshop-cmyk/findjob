"""Dream-company monitor: watch Target-50 career pages directly.

Two channels, both automatic:
  1. Companies with a supported ATS (greenhouse / lever / ashby /
     smartrecruiters / workday) are polled via their PUBLIC job-board APIs —
     no scraping, no LinkedIn dependency, no JSearch quota.
  2. `flag_dream()` marks aggregator-fetched jobs whose employer matches any
     Target-50 name, so even `ats: manual` companies get ⭐ flagged daily.

New postings are keyword-filtered (career/dream_companies.yaml `keywords`)
and deduped in data/dream/seen.json; survivors flow into the daily AI scoring.

CLI:  python -m src.dream            # fetch & print new dream-company matches
      python -m src.dream --all      # ignore dedupe, show everything matching
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import yaml

from .sources.base import Job, clean_html, get_json

ROOT = Path(__file__).resolve().parent.parent
CFG_PATH = ROOT / "career" / "dream_companies.yaml"
SEEN_PATH = ROOT / "data" / "dream" / "seen.json"
SEEN_TTL = 90 * 86400


def load_cfg() -> dict:
    if not CFG_PATH.exists():
        return {"companies": [], "keywords": []}
    return yaml.safe_load(CFG_PATH.read_text()) or {"companies": [], "keywords": []}


# ---------------- per-ATS public APIs ----------------

def _greenhouse(c: dict) -> list[Job]:
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{c['token']}/jobs",
                    params={"content": "true"})
    out = []
    for j in data.get("jobs", []):
        out.append(Job(
            source=f"dream:{c['name']}", title=j.get("title", ""), company=c["name"],
            url=j.get("absolute_url", ""), description=clean_html(j.get("content", ""))[:5000],
            location=(j.get("location") or {}).get("name", ""), posted=j.get("updated_at", "")[:10],
        ))
    return out


def _lever(c: dict) -> list[Job]:
    data = get_json(f"https://api.lever.co/v0/postings/{c['token']}", params={"mode": "json"})
    out = []
    for j in data if isinstance(data, list) else []:
        cat = j.get("categories") or {}
        out.append(Job(
            source=f"dream:{c['name']}", title=j.get("text", ""), company=c["name"],
            url=j.get("hostedUrl", ""), description=clean_html(j.get("descriptionPlain") or j.get("description", ""))[:5000],
            location=cat.get("location", ""),
        ))
    return out


def _ashby(c: dict) -> list[Job]:
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{c['token']}")
    out = []
    for j in data.get("jobs", []):
        out.append(Job(
            source=f"dream:{c['name']}", title=j.get("title", ""), company=c["name"],
            url=j.get("jobUrl") or j.get("applyUrl", ""),
            description=clean_html(j.get("descriptionPlain") or "")[:5000],
            location=j.get("location", ""), remote=bool(j.get("isRemote")),
        ))
    return out


def _smartrecruiters(c: dict) -> list[Job]:
    data = get_json(f"https://api.smartrecruiters.com/v1/companies/{c['token']}/postings",
                    params={"limit": 100})
    out = []
    for j in data.get("content", []):
        loc = j.get("location") or {}
        out.append(Job(
            source=f"dream:{c['name']}", title=j.get("name", ""), company=c["name"],
            url=f"https://jobs.smartrecruiters.com/{c['token']}/{j.get('id', '')}",
            location=", ".join(filter(None, [loc.get("city", ""), loc.get("country", "")])),
            posted=(j.get("releasedDate") or "")[:10],
        ))
    return out


def _workday(c: dict) -> list[Job]:
    """Workday CxS public search API: POST .../wday/cxs/<tenant>/<site>/jobs."""
    import requests
    host, site = c["host"], c["site"]
    tenant = host.split(".")[0]
    url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    out: list[Job] = []
    for kw in ("AI governance", "internal audit", "AI risk"):
        r = requests.post(url, json={"appliedFacets": {}, "limit": 20, "offset": 0,
                                     "searchText": kw}, timeout=25,
                          headers={"Accept": "application/json", "Content-Type": "application/json"})
        r.raise_for_status()
        for j in r.json().get("jobPostings", []):
            path = j.get("externalPath", "")
            out.append(Job(
                source=f"dream:{c['name']}", title=j.get("title", ""), company=c["name"],
                url=f"https://{host}/en-US/{site}{path}",
                location=j.get("locationsText", ""), posted=j.get("postedOn", ""),
            ))
    return out


FETCHERS = {
    "greenhouse": _greenhouse,
    "lever": _lever,
    "ashby": _ashby,
    "smartrecruiters": _smartrecruiters,
    "workday": _workday,
}


# ---------------- pipeline ----------------

def _kw_match(job: Job, keywords: list[str]) -> bool:
    blob = f"{job.title} {job.description}".lower()
    return any(k.lower() in blob for k in keywords)


def _load_seen() -> dict[str, float]:
    if SEEN_PATH.exists():
        try:
            return json.loads(SEEN_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save_seen(seen: dict[str, float]) -> None:
    now = time.time()
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(json.dumps({k: v for k, v in seen.items() if now - v < SEEN_TTL}))


def fetch_new(mark_seen: bool = True, ignore_seen: bool = False) -> list[Job]:
    """Poll all ATS-backed dream companies; return NEW keyword-matching postings."""
    cfg = load_cfg()
    keywords = cfg.get("keywords", [])
    seen = _load_seen()
    now = time.time()
    fresh: list[Job] = []
    polled = failed = 0

    for c in cfg.get("companies", []):
        fn = FETCHERS.get(c.get("ats", "manual"))
        if not fn:
            continue
        polled += 1
        try:
            jobs = fn(c)
        except Exception as e:
            failed += 1
            print(f"  dream: {c['name']} ({c.get('ats')}) failed: {e}", file=sys.stderr)
            continue
        tier = int(c.get("tier", 2))
        for j in jobs:
            if keywords and not _kw_match(j, keywords):
                continue
            j.dream, j.dream_tier = True, tier
            if not ignore_seen and j.id in seen:
                continue
            seen[j.id] = now
            fresh.append(j)

    print(f"  dream: polled {polled} ATS boards ({failed} failed), {len(fresh)} new matches", file=sys.stderr)
    if mark_seen and not ignore_seen:
        _save_seen(seen)
    return fresh


def flag_dream(jobs: list[Job]) -> int:
    """Channel 2: mark aggregator jobs whose employer is on the Target-50 list."""
    cfg = load_cfg()
    names = {}
    for c in cfg.get("companies", []):
        names[c["name"].lower()] = int(c.get("tier", 2))
    n = 0
    for j in jobs:
        comp = (j.company or "").lower().strip()
        if not comp:
            continue
        for name, tier in names.items():
            if name in comp or comp in name:
                j.dream, j.dream_tier = True, tier
                n += 1
                break
    return n


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="忽略去重，显示全部命中")
    args = ap.parse_args()
    jobs = fetch_new(mark_seen=False, ignore_seen=args.all)
    for j in sorted(jobs, key=lambda x: x.dream_tier):
        print(f"[T{j.dream_tier}] {j.company} — {j.title} ({j.location})\n     {j.url}")
    if not jobs:
        print("(无新岗位)")


if __name__ == "__main__":
    main()
