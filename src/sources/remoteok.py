"""RemoteOK — public JSON feed at https://remoteok.com/api"""
from __future__ import annotations

from .base import Job, clean_html, get_json


def fetch(cfg: dict) -> list[Job]:
    data = get_json("https://remoteok.com/api")
    jobs: list[Job] = []
    for item in data:
        # first element is a legal/notice object, not a job
        if not isinstance(item, dict) or "position" not in item:
            continue
        jobs.append(
            Job(
                source="RemoteOK",
                title=item.get("position", ""),
                company=item.get("company", ""),
                url=item.get("url", "") or item.get("apply_url", ""),
                description=clean_html(item.get("description", "")),
                location=item.get("location", "") or "Remote",
                remote=True,
                tags=[str(t) for t in item.get("tags", []) if t],
                posted=item.get("date", "")[:10],
            )
        )
    return jobs
