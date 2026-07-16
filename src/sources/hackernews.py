"""Hacker News monthly "Ask HN: Who is hiring?" thread via the Algolia API.

Each top-level comment is one job posting. Noisy, but high signal for remote /
startup roles. We fetch the latest hiring thread and turn each comment into a Job.
"""
from __future__ import annotations

import re

from .base import Job, clean_html, get_json

_FIRST_LINE = re.compile(r"^(.*?)(?:\.|\n|\||—|-\s)", re.S)


def _latest_thread_id() -> str | None:
    data = get_json(
        "https://hn.algolia.com/api/v1/search_by_date",
        params={"query": "Ask HN: Who is hiring?", "tags": "story", "hitsPerPage": 1},
    )
    hits = data.get("hits", [])
    return hits[0]["objectID"] if hits else None


def fetch(cfg: dict) -> list[Job]:
    thread_id = _latest_thread_id()
    if not thread_id:
        return []
    data = get_json(
        "https://hn.algolia.com/api/v1/search",
        params={"tags": f"comment,story_{thread_id}", "hitsPerPage": 200},
    )
    jobs: list[Job] = []
    for hit in data.get("hits", []):
        text = clean_html(hit.get("comment_text", ""))
        if not text or len(text) < 40:
            continue
        m = _FIRST_LINE.match(text)
        headline = (m.group(1) if m else text)[:120].strip()
        jobs.append(
            Job(
                source="HN Who-is-hiring",
                title=headline,
                company="(see post)",
                url=f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                description=text,
                location="",
                remote="remote" in text.lower(),
                tags=[],
                posted=(hit.get("created_at", "") or "")[:10],
            )
        )
    return jobs
