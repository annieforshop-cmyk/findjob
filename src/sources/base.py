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

    # filled in by the scorer
    score: float = 0.0
    matched: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        """Stable id for cross-day dedupe. Prefer URL, fall back to title+company."""
        basis = (self.url or f"{self.title}|{self.company}").strip().lower()
        return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]

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
