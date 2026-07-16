"""Shared job model + HTTP helpers for all sources."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from typing import Any

import requests

UA = "findjob/1.0 (+https://github.com/annieforshop-cmyk/findjob)"
TIMEOUT = 25

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def clean_html(text: str | None) -> str:
    """Strip tags / collapse whitespace so JD text is scoreable + emailable."""
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&nbsp;", " ")
        .replace("&#39;", "'")
        .replace("&quot;", '"')
    )
    return _WS_RE.sub(" ", text).strip()


@dataclass
class Job:
    source: str
    title: str
    company: str
    url: str
    description: str = ""
    location: str = ""
    remote: bool = False
    tags: list[str] = field(default_factory=list)
    posted: str = ""  # ISO date string if known

    # filled in by the keyword scorer
    score: float = 0.0
    matched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    # filled in by the LLM semantic analyst (ai_score.py); -1 = not AI-scored
    ai_score: float = -1.0          # overall fit 0-100
    ai_skills: float = -1.0         # skill/content fit
    ai_seniority: float = -1.0      # level fit (vs candidate's real seniority band)
    ai_years_fit: float = -1.0      # years-of-experience fit
    ai_reason: str = ""             # one-line why
    ai_recommendation: str = ""     # apply / maybe / skip
    ai_location_ok: bool = True     # US-based & commute/remote acceptable
    ai_location_note: str = ""
    ai_salary: str = ""             # extracted or estimated range
    ai_ghost_risk: str = ""         # low / medium / high
    ai_company_note: str = ""       # brief reputation/context

    @property
    def id(self) -> str:
        """Stable id for cross-day dedupe. Prefer URL, fall back to title+company."""
        basis = (self.url or f"{self.title}|{self.company}").strip().lower()
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]

    @property
    def rank_score(self) -> float:
        """AI fit if it ran, otherwise the keyword score."""
        return self.ai_score if self.ai_score >= 0 else self.score

    @property
    def blob(self) -> str:
        """Everything a scorer should look at, lowercased."""
        return " ".join(
            [self.title, self.company, self.location, self.description, " ".join(self.tags)]
        ).lower()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["id"] = self.id
        return d


def get_queries(cfg: dict) -> list[str]:
    """Search terms used by all aggregator sources (jsearch / adzuna).
    Prefer the profile's top-level `queries`, then jsearch.queries, then titles."""
    return (
        cfg.get("queries")
        or (cfg.get("jsearch", {}) or {}).get("queries")
        or cfg.get("target_titles", [])[:3]
    )


def get_json(url: str, params: dict | None = None, headers: dict | None = None) -> Any:
    h = {"User-Agent": UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    r = requests.get(url, params=params, headers=h, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_text(url: str, headers: dict | None = None) -> str:
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    r = requests.get(url, headers=h, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text
