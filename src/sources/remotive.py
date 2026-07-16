"""Remotive — public JSON API at https://remotive.com/api/remote-jobs"""
from __future__ import annotations

from .base import Job, clean_html, get_json


def fetch(cfg: dict) -> list[Job]:
    data = get_json("https://remotive.com/api/remote-jobs")
    jobs: list[Job] = []
    for item in data.get("jobs", []):
        jobs.append(
            Job(
                source="Remotive",
                title=item.get("title", ""),
                company=item.get("company_name", ""),
                url=item.get("url", ""),
                description=clean_html(item.get("description", "")),
                location=item.get("candidate_required_location", "") or "Remote",
                remote=True,
                tags=item.get("tags", []) or [],
                posted=(item.get("publication_date", "") or "")[:10],
            )
        )
    return jobs
