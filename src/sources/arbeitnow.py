"""Arbeitnow — public JSON board at https://www.arbeitnow.com/api/job-board-api"""
from __future__ import annotations

from .base import Job, clean_html, get_json


def fetch(cfg: dict) -> list[Job]:
    jobs: list[Job] = []
    url = "https://www.arbeitnow.com/api/job-board-api"
    for _ in range(3):  # up to 3 pages
        data = get_json(url)
        for item in data.get("data", []):
            jobs.append(
                Job(
                    source="Arbeitnow",
                    title=item.get("title", ""),
                    company=item.get("company_name", ""),
                    url=item.get("url", ""),
                    description=clean_html(item.get("description", "")),
                    location=item.get("location", ""),
                    remote=bool(item.get("remote", False)),
                    tags=item.get("tags", []) or [],
                    posted="",
                )
            )
        url = (data.get("links", {}) or {}).get("next") or ""
        if not url:
            break
    return jobs
