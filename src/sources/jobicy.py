"""Jobicy — public JSON API at https://jobicy.com/api/v2/remote-jobs"""
from __future__ import annotations

from .base import Job, clean_html, get_json


def fetch(cfg: dict) -> list[Job]:
    data = get_json("https://jobicy.com/api/v2/remote-jobs", params={"count": 100})
    jobs: list[Job] = []
    for item in data.get("jobs", []):
        jobs.append(
            Job(
                source="Jobicy",
                title=item.get("jobTitle", ""),
                company=item.get("companyName", ""),
                url=item.get("url", ""),
                description=clean_html(item.get("jobDescription", "") or item.get("jobExcerpt", "")),
                location=item.get("jobGeo", "") or "Remote",
                remote=True,
                tags=(item.get("jobIndustry", []) or []) + (item.get("jobType", []) or []),
                posted=(item.get("pubDate", "") or "")[:10],
            )
        )
    return jobs
