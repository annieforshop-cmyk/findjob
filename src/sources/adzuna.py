"""Adzuna — aggregator (includes some Indeed-sourced roles). Free API key required.

Set ADZUNA_APP_ID / ADZUNA_APP_KEY as env vars / GitHub Secrets and flip
sources.adzuna=true in config.yaml.
"""
from __future__ import annotations

import os

from .base import Job, clean_html, get_json


def fetch(cfg: dict) -> list[Job]:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        raise RuntimeError("adzuna enabled but ADZUNA_APP_ID / ADZUNA_APP_KEY not set")

    acfg = cfg.get("adzuna", {}) or {}
    country = acfg.get("country", "us")
    data = get_json(
        f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",
        params={
            "app_id": app_id,
            "app_key": app_key,
            "what": acfg.get("what", " ".join(cfg.get("target_titles", [])[:1])),
            "results_per_page": acfg.get("results_per_page", 50),
            "content-type": "application/json",
        },
    )
    jobs: list[Job] = []
    for item in data.get("results", []):
        loc = ((item.get("location") or {}).get("display_name")) or ""
        jobs.append(
            Job(
                source="Adzuna",
                title=item.get("title", ""),
                company=((item.get("company") or {}).get("display_name")) or "",
                url=item.get("redirect_url", ""),
                description=clean_html(item.get("description", "")),
                location=loc,
                remote="remote" in (loc + item.get("title", "")).lower(),
                tags=[((item.get("category") or {}).get("label")) or ""],
                posted=(item.get("created", "") or "")[:10],
            )
        )
    return jobs
