"""ATS 直连源：每天扫 career/ats_companies.yaml 里所有公司的官网招聘接口。

不需要任何 API key —— Greenhouse / Lever / Ashby / SmartRecruiters 的 job-board
API 和 Workday 的 CxS 搜索接口都是公开的。聚合器(JSearch/Adzuna)的 key 失效时，
这个源保证管道仍然有大量真实岗位可打分（广撒网，公司多样性由此而来）。

一次进程内只抓一遍（三个 profile 共享结果），单个公司失败不影响其他公司。
"""
from __future__ import annotations

import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
import yaml

from .base import Job, clean_html

ROOT = Path(__file__).resolve().parent.parent.parent
CFG_PATH = ROOT / "career" / "ats_companies.yaml"
TIMEOUT = 25
WORKERS = 8                # 温和的并发度，避免触发限流
DETAILS_PER_COMPANY = 25   # Workday/SmartRecruiters 列表无 JD，最多补抓多少个详情页

# Workday 接口是搜索式的：用覆盖三个方向的核心词查询（profile 无关，可缓存）
WORKDAY_QUERIES = (
    "internal audit", "AI governance", "AI risk",
    "model risk", "operational risk", "compliance",
)

# 反爬/限流防护：
#  - 这些全是各 ATS 官方公开的 job-board API（本就是给外部集成用的），不是页面爬取
#  - 仍然保持礼貌：浏览器式 UA、请求间随机抖动、429/403 时退避重试一次
_HDRS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}
_cache: list[Job] | None = None


def _pause() -> None:
    time.sleep(random.uniform(0.15, 0.45))


def _req(method: str, url: str, **kw) -> requests.Response:
    """一次礼貌请求：抖动 + 限流时退避重试一次。"""
    _pause()
    r = requests.request(method, url, timeout=TIMEOUT, **kw)
    if r.status_code in (429, 403):
        time.sleep(random.uniform(4, 8))
        r = requests.request(method, url, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r


def _gh(c: dict) -> list[Job]:
    r = _req("GET", f"https://boards-api.greenhouse.io/v1/boards/{c['token']}/jobs",
             params={"content": "true"}, headers=_HDRS)
    return [Job(source=f"ats:{c['name']}", title=j.get("title", ""), company=c["name"],
                url=j.get("absolute_url", ""),
                description=clean_html(j.get("content", ""))[:5000],
                location=(j.get("location") or {}).get("name", ""),
                posted=(j.get("updated_at") or "")[:10])
            for j in r.json().get("jobs", [])]


def _lever(c: dict) -> list[Job]:
    r = _req("GET", f"https://api.lever.co/v0/postings/{c['token']}",
             params={"mode": "json"}, headers=_HDRS)
    data = r.json()
    return [Job(source=f"ats:{c['name']}", title=j.get("text", ""), company=c["name"],
                url=j.get("hostedUrl", ""),
                description=clean_html(j.get("descriptionPlain") or j.get("description", ""))[:5000],
                location=(j.get("categories") or {}).get("location", ""))
            for j in (data if isinstance(data, list) else [])]


def _ashby(c: dict) -> list[Job]:
    r = _req("GET", f"https://api.ashbyhq.com/posting-api/job-board/{c['token']}",
             headers=_HDRS)
    return [Job(source=f"ats:{c['name']}", title=j.get("title", ""), company=c["name"],
                url=j.get("jobUrl") or j.get("applyUrl", ""),
                description=clean_html(j.get("descriptionPlain") or "")[:5000],
                location=j.get("location", ""), remote=bool(j.get("isRemote")))
            for j in r.json().get("jobs", [])]


def _smart(c: dict) -> list[Job]:
    r = _req("GET", f"https://api.smartrecruiters.com/v1/companies/{c['token']}/postings",
             params={"limit": 100}, headers=_HDRS)
    out = []
    for j in r.json().get("content", []):
        loc = j.get("location") or {}
        out.append(Job(source=f"ats:{c['name']}", title=j.get("name", ""), company=c["name"],
                       url=f"https://jobs.smartrecruiters.com/{c['token']}/{j.get('id', '')}",
                       location=", ".join(filter(None, [loc.get("city", ""),
                                                        (loc.get("country") or "").upper()])),
                       posted=(j.get("releasedDate") or "")[:10],
                       tags=[str(j.get("id", ""))]))
    # 列表接口没有 JD 正文——为前 N 个补抓详情（内容匹配和"从 JD 判断地点"都需要）
    for j in out[:DETAILS_PER_COMPANY]:
        try:
            rid = j.tags[0]
            d = _req("GET", f"https://api.smartrecruiters.com/v1/companies/{c['token']}/postings/{rid}",
                     headers=_HDRS).json()
            parts = ((d.get("jobAd") or {}).get("sections") or {})
            j.description = clean_html(" ".join(
                str(v.get("text", "")) for v in parts.values() if isinstance(v, dict)))[:5000]
        except Exception:
            continue
    return out


def _workday(c: dict) -> list[Job]:
    host, site = c["host"], c["site"]
    tenant = host.split(".")[0]
    url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    out, seen = [], set()
    for kw in WORKDAY_QUERIES:
        r = _req("POST", url, json={"appliedFacets": {}, "limit": 20, "offset": 0,
                                    "searchText": kw},
                 headers={**_HDRS, "Content-Type": "application/json"})
        for j in r.json().get("jobPostings", []):
            path = j.get("externalPath", "")
            if not path or path in seen:
                continue
            seen.add(path)
            out.append(Job(source=f"ats:{c['name']}", title=j.get("title", ""),
                           company=c["name"], url=f"https://{host}/en-US/{site}{path}",
                           location=j.get("locationsText", ""),
                           posted=j.get("postedOn", ""),
                           tags=[path]))
    if not out:
        raise RuntimeError("0 postings — host/site 可能失效")
    # 搜索接口没有 JD 正文——补抓详情：没有正文，内容匹配层会误杀这些岗位，
    # 而且"从 JD 全文判断可用地点"也需要正文
    for j in out[:DETAILS_PER_COMPANY]:
        try:
            d = _req("GET", f"https://{host}/wday/cxs/{tenant}/{site}{j.tags[0]}",
                     headers=_HDRS).json()
            info = d.get("jobPostingInfo") or {}
            j.description = clean_html(info.get("jobDescription", ""))[:5000]
            extra_loc = info.get("additionalLocations") or []
            if extra_loc:
                j.location = ", ".join([j.location] + [str(x) for x in extra_loc])[:300]
        except Exception:
            continue
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
