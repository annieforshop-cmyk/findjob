"""The Muse — public jobs API at https://www.themuse.com/api/public/jobs

Free, no API key required. Good coverage of professional / corporate roles
(finance, legal, risk, compliance, data), which fits senior non-engineering
job searches better than the remote-tech boards.

The public API filters by level / category / location / company — it has no
free-text keyword search — so we pull recent senior/management postings and
let score.py decide fit. One page ≈ 20 jobs.
"""
from __future__ import annotations

from .base import Job, clean_html, get_json

API = "https://www.themuse.com/api/public/jobs"

# The Muse level names (exact strings the API expects). Senior/management by
# default — matches this candidate's band and keeps volume sane.
DEFAULT_LEVELS = ["Senior Level", "Management"]


def _loc(item: dict) -> str:
    locs = [l.get("name", "") for l in (item.get("locations") or []) if l.get("name")]
    return ", ".join(locs)


def fetch(cfg: dict) -> list[Job]:
    mcfg = cfg.get("themuse", {}) or {}
    levels = mcfg.get("levels", DEFAULT_LEVELS)
    categories = mcfg.get("categories")  # optional list; None = all categories
    max_pages = int(mcfg.get("max_pages", 3))

    jobs: list[Job] = []
    for page in range(1, max_pages + 1):
        params: dict = {"page": page, "descending": "true"}
        if levels:
            params["level"] = levels
        if categories:
            params["category"] = categories
        data = get_json(API, params=params)
        results = data.get("results", []) or []
        if not results:
            break
        for item in results:
            company = (item.get("company") or {}).get("name", "")
            refs = item.get("refs") or {}
            loc = _loc(item)
            is_remote = "remote" in loc.lower() or "flexible" in loc.lower()
            jobs.append(
                Job(
                    source="The Muse",
                    title=item.get("name", ""),
                    company=company,
                    url=refs.get("landing_page", ""),
                    description=clean_html(item.get("contents", "")),
                    location=loc or ("Remote" if is_remote else ""),
                    remote=is_remote,
                    tags=[c.get("name", "") for c in (item.get("categories") or [])],
                    posted=(item.get("publication_date", "") or "")[:10],
                )
            )
        # stop early if we've passed the last page
        if page >= int(data.get("page_count", page)):
            break
    return jobs
