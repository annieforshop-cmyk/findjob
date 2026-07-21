"""JSearch (RapidAPI) — aggregates Google-for-Jobs results, which include
LinkedIn, Indeed, Glassdoor and ZipRecruiter postings.

This is the clean, ToS-respecting way to get "LinkedIn / Indeed" coverage
without scraping. Requires a free RapidAPI key:
  1. Sign up at rapidapi.com, subscribe to "JSearch" (has a free tier).
  2. Set RAPIDAPI_KEY as an env var / GitHub Secret.
  3. In config.yaml set sources.jsearch=true and list jsearch.queries.
"""
from __future__ import annotations

import os

from .base import Job, clean_html, get_json, get_queries

HOST = "jsearch.p.rapidapi.com"


def fetch(cfg: dict) -> list[Job]:
    key = os.environ.get("RAPIDAPI_KEY")
    if not key:
        raise RuntimeError("jsearch enabled but RAPIDAPI_KEY not set")

    jcfg = cfg.get("jsearch", {}) or {}
    queries = get_queries(cfg)
    num_pages = int(jcfg.get("num_pages", 1))
    remote_only = bool(cfg.get("remote_only", False))
    country = jcfg.get("country", "us")
    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": HOST}

    jobs: list[Job] = []
    for q in queries:
        try:
            data = get_json(
                f"https://{HOST}/search",
                params={
                    "query": f"{q} in USA" if "in " not in q.lower() else q,
                    "page": 1,
                    "num_pages": num_pages,
                    "country": country,
                    "date_posted": jcfg.get("date_posted", "week"),
                    "remote_jobs_only": "true" if remote_only else "false",
                },
                headers=headers,
            )
        except Exception as e:
            if "404" in str(e):
                raise RuntimeError(
                    "JSearch 返回 404 —— 通常是 RapidAPI 账号没有订阅 JSearch"
                    "（或订阅已失效/被下架）。请登录 rapidapi.com → 搜 JSearch → "
                    "Subscribe（有免费档），确认后 RAPIDAPI_KEY 才会生效。"
                ) from e
            raise
        for item in data.get("data", []):
            city = item.get("job_city") or ""
            state = item.get("job_state") or ""
            country = item.get("job_country") or ""
            loc = ", ".join(p for p in (city, state, country) if p)
            publisher = item.get("job_publisher") or "JSearch"
            jobs.append(
                Job(
                    source=f"{publisher} (via JSearch)",
                    title=item.get("job_title", ""),
                    company=item.get("employer_name", ""),
                    url=item.get("job_apply_link", "") or item.get("job_google_link", ""),
                    description=clean_html(item.get("job_description", "")),
                    location=loc or ("Remote" if item.get("job_is_remote") else ""),
                    remote=bool(item.get("job_is_remote")),
                    tags=[item.get("job_employment_type", "") or ""],
                    posted=(item.get("job_posted_at_datetime_utc", "") or "")[:10],
                )
            )
    return jobs
