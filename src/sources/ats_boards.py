"""ATS 直连源：每天扫 career/ats_companies.yaml 里所有公司的官网招聘接口。

不需要任何 API key —— Greenhouse / Lever / Ashby / SmartRecruiters 的 job-board
API 和 Workday 的 CxS 搜索接口都是公开的。聚合器(JSearch/Adzuna)的 key 失效时，
这个源保证管道仍然有大量真实岗位可打分（广撒网，公司多样性由此而来）。

一次进程内只抓一遍（三个 profile 共享结果），单个公司失败不影响其他公司。
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
import yaml

from .base import Job, clean_html


def _workday_date(s: str) -> str:
    """Workday returns relative posted text ('Posted Today', 'Posted 13 Days
    Ago', 'Posted 30+ Days Ago'). Convert to an ISO date so freshness scoring
    and the email display work like every other source. Unknown -> ''."""
    if not s:
        return ""
    low = s.lower()
    today = dt.date.today()
    if "today" in low:
        return today.isoformat()
    if "yesterday" in low:
        return (today - dt.timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)\+?\s*day", low)
    if m:
        return (today - dt.timedelta(days=int(m.group(1)))).isoformat()
    m = re.search(r"(\d+)\+?\s*month", low)
    if m:
        return (today - dt.timedelta(days=30 * int(m.group(1)))).isoformat()
    return s[:10] if re.match(r"\d{4}-\d{2}-\d{2}", s) else ""

ROOT = Path(__file__).resolve().parent.parent.parent
CFG_PATH = ROOT / "career" / "ats_companies.yaml"
TIMEOUT = 25
WORKERS = 24     # bumped for a larger verified company list (see verify_boards.py)

# Workday 接口是搜索式的：用覆盖三个方向的核心词查询（profile 无关，可缓存）
WORKDAY_QUERIES = (
    "internal audit", "AI governance", "AI risk",
    "model risk", "operational risk", "compliance",
)

_HDRS = {"User-Agent": "findjob/1.0", "Accept": "application/json"}
_cache: list[Job] | None = None


def _gh(c: dict) -> list[Job]:
    r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{c['token']}/jobs",
                     params={"content": "true"}, headers=_HDRS, timeout=TIMEOUT)
    r.raise_for_status()
    return [Job(source=f"ats:{c['name']}", title=j.get("title", ""), company=c["name"],
                url=j.get("absolute_url", ""),
                description=clean_html(j.get("content", ""))[:5000],
                location=(j.get("location") or {}).get("name", ""),
                posted=(j.get("updated_at") or "")[:10])
            for j in r.json().get("jobs", [])]


def _lever(c: dict) -> list[Job]:
    r = requests.get(f"https://api.lever.co/v0/postings/{c['token']}",
                     params={"mode": "json"}, headers=_HDRS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return [Job(source=f"ats:{c['name']}", title=j.get("text", ""), company=c["name"],
                url=j.get("hostedUrl", ""),
                description=clean_html(j.get("descriptionPlain") or j.get("description", ""))[:5000],
                location=(j.get("categories") or {}).get("location", ""))
            for j in (data if isinstance(data, list) else [])]


def _ashby(c: dict) -> list[Job]:
    r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{c['token']}",
                     headers=_HDRS, timeout=TIMEOUT)
    r.raise_for_status()
    return [Job(source=f"ats:{c['name']}", title=j.get("title", ""), company=c["name"],
                url=j.get("jobUrl") or j.get("applyUrl", ""),
                description=clean_html(j.get("descriptionPlain") or "")[:5000],
                location=j.get("location", ""), remote=bool(j.get("isRemote")))
            for j in r.json().get("jobs", [])]


def _smart(c: dict) -> list[Job]:
    r = requests.get(f"https://api.smartrecruiters.com/v1/companies/{c['token']}/postings",
                     params={"limit": 100}, headers=_HDRS, timeout=TIMEOUT)
    r.raise_for_status()
    out = []
    for j in r.json().get("content", []):
        loc = j.get("location") or {}
        out.append(Job(source=f"ats:{c['name']}", title=j.get("name", ""), company=c["name"],
                       url=f"https://jobs.smartrecruiters.com/{c['token']}/{j.get('id', '')}",
                       location=", ".join(filter(None, [loc.get("city", ""),
                                                        (loc.get("country") or "").upper()])),
                       posted=(j.get("releasedDate") or "")[:10]))
    return out


def _workday(c: dict) -> list[Job]:
    host, site = c["host"], c["site"]
    tenant = host.split(".")[0]
    url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    out, seen = [], set()
    for kw in WORKDAY_QUERIES:
        r = requests.post(url, json={"appliedFacets": {}, "limit": 20, "offset": 0,
                                     "searchText": kw},
                          headers={**_HDRS, "Content-Type": "application/json"},
                          timeout=TIMEOUT)
        r.raise_for_status()
        for j in r.json().get("jobPostings", []):
            path = j.get("externalPath", "")
            if not path or path in seen:
                continue
            seen.add(path)
            out.append(Job(source=f"ats:{c['name']}", title=j.get("title", ""),
                           company=c["name"], url=f"https://{host}/en-US/{site}{path}",
                           location=j.get("locationsText", ""),
                           posted=_workday_date(j.get("postedOn", ""))))
    if not out:
        raise RuntimeError("0 postings — host/site 可能失效")
    return out


_FETCHERS = {"greenhouse": _gh, "lever": _lever, "ashby": _ashby,
             "smartrecruiters": _smart, "workday": _workday}


def fetch(cfg: dict) -> list[Job]:
    global _cache
    if _cache is not None:
        return list(_cache)
    if not CFG_PATH.exists():
        return []
    companies = (yaml.safe_load(CFG_PATH.read_text()) or {}).get("companies", [])
    jobs: list[Job] = []
    failed = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(_FETCHERS[c["kind"]], c): c
                for c in companies if c.get("kind") in _FETCHERS}
        for f in as_completed(futs):
            c = futs[f]
            try:
                jobs.extend(f.result())
            except Exception as e:
                failed.append(f"{c['name']}: {str(e)[:60]}")
    if failed:
        print(f"  ats_boards: {len(failed)} boards failed — " + "; ".join(failed[:8]),
              file=sys.stderr)
    print(f"  ats_boards: {len(companies) - len(failed)} boards ok, {len(jobs)} raw jobs",
          file=sys.stderr)
    _cache = jobs
    return list(jobs)
