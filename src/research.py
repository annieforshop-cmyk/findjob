"""Company Research Agent — 申请前自动尽调一家公司.

Inputs (free, no keys needed for news):
  - Google News RSS: recent headlines (layoffs, funding, strategy, AI moves)
  - The LLM's own knowledge of the company (labeled as needing verification)
  - Optionally the specific JD being targeted

Output: a structured brief — strategy & AI posture, layoff risk, funding,
who likely leads the relevant team, Glassdoor/Blind themes to verify,
cover-letter hooks, interview angles. Cached in data/research/ for 14 days
so the daily brief doesn't re-pay for the same company.

CLI:
  python -m src.research "Citi"                    # full brief to stdout
  python -m src.research "Citi" --title "AI Governance Director"
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "research"
CACHE_TTL = 14 * 86400

SYSTEM = """You are a sharp company-research analyst helping a senior internal
audit / AI governance candidate decide whether and how to apply. Synthesize the
provided news headlines with what you genuinely know about the company. Be
honest about uncertainty: mark anything from memory that may be stale as
needing verification. Never invent news, numbers, or names. Return ONLY JSON."""

USER_TMPL = """COMPANY: {company}
{role_line}
RECENT NEWS HEADLINES (Google News, newest first — your freshest signal):
{news}

CANDIDATE CONTEXT: senior manager/director-level internal auditor (CPA, ~10 yrs
banking) pivoting deeper into AI governance / AI risk. Cares about: AI strategy
maturity, governance investment, stability, and a path to Head of AI Governance.

Return JSON:
{{
 "summary": "<=40 words: what this company is, current trajectory",
 "ai_posture": "<=40 words: their AI strategy / responsible-AI / governance investment, as far as known",
 "recent_signals": ["<=3 bullets distilled from the headlines: strategy moves, leadership changes, regulatory events"],
 "layoff_risk": "<low|medium|high> — recent layoffs/restructuring in or near this function",
 "funding_health": "<=20 words: profitability/funding/stock trend if known, else 'unknown'",
 "team_to_find": ["2-3 titles of the people who likely own this hire, e.g. 'Chief Audit Executive', 'Head of Responsible AI'"],
 "culture_flags": ["<=3 themes commonly reported on Glassdoor/Blind for this employer — label as 'to verify' if from memory"],
 "cover_letter_hooks": ["2-3 specific, TRUE angles connecting this company's situation to the candidate's background"],
 "interview_angles": ["2-3 smart questions/points the candidate can raise to look exceptionally prepared"]
}}"""


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def fetch_news(company: str, limit: int = 8) -> list[str]:
    """Recent headlines from Google News RSS (no key needed)."""
    try:
        r = requests.get(
            "https://news.google.com/rss/search",
            params={"q": f'"{company}"', "hl": "en-US", "gl": "US", "ceid": "US:en"},
            timeout=20, headers={"User-Agent": "findjob/1.0"},
        )
        r.raise_for_status()
        root = ET.fromstring(r.content)
        items = []
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            date = (item.findtext("pubDate") or "")[:16]
            if title:
                items.append(f"[{date}] {title}")
            if len(items) >= limit:
                break
        return items
    except Exception as e:
        print(f"  research: news fetch failed for {company}: {e}", file=sys.stderr)
        return []


def _cache_get(company: str) -> dict | None:
    p = CACHE_DIR / f"{_slug(company)}.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
            if time.time() - data.get("_ts", 0) < CACHE_TTL:
                return data
        except Exception:
            pass
    return None


def _cache_put(company: str, data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data["_ts"] = time.time()
    (CACHE_DIR / f"{_slug(company)}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))


def brief(company: str, title: str = "", use_cache: bool = True) -> dict | None:
    """Research brief for a company. None if no LLM key AND no news."""
    if use_cache:
        cached = _cache_get(company)
        if cached:
            return cached

    news = fetch_news(company)
    try:
        from openai import OpenAI
    except ImportError:
        OpenAI = None
    if OpenAI is None or not os.environ.get("OPENAI_API_KEY"):
        if not news:
            return None
        data = {"summary": "", "recent_signals": news[:3], "company": company}
        return data

    client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    role_line = f"TARGET ROLE: {title}" if title else ""
    try:
        resp = client.chat.completions.create(
            model=model, temperature=0.3,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER_TMPL.format(
                    company=company, role_line=role_line,
                    news="\n".join(news) or "(no recent headlines found)",
                )},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
    except Exception as e:
        print(f"  research: LLM failed for {company}: {e}", file=sys.stderr)
        return {"summary": "", "recent_signals": news[:3], "company": company} if news else None
    data["company"] = company
    _cache_put(company, data)
    return data


def render_text(b: dict) -> str:
    if not b:
        return ""
    lines = [f"◆ {b.get('company', '')} 尽调"]
    if b.get("summary"):
        lines.append(f"  概况: {b['summary']}")
    if b.get("ai_posture"):
        lines.append(f"  AI 布局: {b['ai_posture']}")
    for s in b.get("recent_signals", []):
        lines.append(f"  · {s}")
    if b.get("layoff_risk"):
        lines.append(f"  裁员风险: {b['layoff_risk']} | 财务: {b.get('funding_health', '?')}")
    if b.get("team_to_find"):
        lines.append(f"  该找的人: {', '.join(b['team_to_find'])}")
    for c in b.get("culture_flags", []):
        lines.append(f"  文化信号: {c}")
    for h in b.get("cover_letter_hooks", []):
        lines.append(f"  ✍ CL 切入点: {h}")
    for a in b.get("interview_angles", []):
        lines.append(f"  🎤 面试角度: {a}")
    return "\n".join(lines)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("company")
    ap.add_argument("--title", default="")
    ap.add_argument("--fresh", action="store_true", help="跳过缓存重新研究")
    args = ap.parse_args()
    b = brief(args.company, args.title, use_cache=not args.fresh)
    if not b:
        sys.exit("没有拿到任何研究结果（无 OPENAI_API_KEY 且新闻抓取失败）")
    print(render_text(b))


if __name__ == "__main__":
    main()
