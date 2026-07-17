"""Networking Agent — referral > 海投.

For any target company it generates, with zero thinking required:
  - LinkedIn alumni searches (your schools × that company)
  - ex-colleague searches (your past employers × that company)
  - decision-maker searches (CAE / Head of AI Governance / Model Risk ...)
  - recruiter searches at that company
  - ready-to-edit outreach message drafts (connection note + follow-up)

Also drives the Recruiter Pipeline: reads career/recruiters.yaml, computes
who is DUE for a touch (cadence) and builds this week's new-connection plan.

CLI:
  python -m src.network --company "Citi"            # links + drafts
  python -m src.network --recruiters                # pipeline status
"""
from __future__ import annotations

import datetime as dt
import urllib.parse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
NETWORK_PATH = ROOT / "career" / "network.yaml"
RECRUITERS_PATH = ROOT / "career" / "recruiters.yaml"


def _load(path: Path) -> dict:
    if path.exists():
        return yaml.safe_load(path.read_text()) or {}
    return {}


def _li_people(keywords: str) -> str:
    return ("https://www.linkedin.com/search/results/people/?keywords="
            + urllib.parse.quote(keywords))


def _li_school(school_slug: str, company: str) -> str:
    return (f"https://www.linkedin.com/school/{school_slug}/people/?keywords="
            + urllib.parse.quote(company))


def links_for_company(company: str) -> dict[str, list[dict]]:
    """All the 'who to contact' searches for one target company."""
    net = _load(NETWORK_PATH)
    out: dict[str, list[dict]] = {"alumni": [], "ex_colleagues": [], "decision_makers": [], "recruiters": []}

    for s in net.get("schools", []):
        out["alumni"].append({
            "label": f"{s['name']} 校友 @ {company}",
            "url": _li_school(s.get("linkedin_school", ""), company),
        })
    for pc in net.get("past_companies", []):
        out["ex_colleagues"].append({
            "label": f"前 {pc['name']} 同事，现在 {company}",
            "url": _li_people(f'"{pc["name"]}" "{company}"'),
        })
    for role in (net.get("target_roles") or [])[:6]:
        out["decision_makers"].append({
            "label": f"{company} · {role}",
            "url": _li_people(f'"{company}" "{role}"'),
        })
    out["recruiters"].append({
        "label": f"{company} 内部 recruiter（audit/risk/AI）",
        "url": _li_people(f'"{company}" recruiter (audit OR risk OR "AI governance")'),
    })
    return out


def outreach_drafts(company: str, title: str = "", relationship: str = "alumni") -> dict[str, str]:
    """Short, human, honest drafts. <=300 chars for connection notes."""
    role = title or "AI governance / internal audit roles"
    openers = {
        "alumni": (f"Hi — fellow Clark alum here. I lead AI governance audit work at a large "
                   f"investment bank and I'm exploring {role} at {company}. Would love to connect "
                   f"and hear how the team there approaches it."),
        "ex_colleague": (f"Hi — we overlapped at BNY Mellon a few years back. I've since been leading "
                         f"AI governance / audit work at a large investment bank, and I'm looking at "
                         f"{role} at {company}. Would be great to reconnect."),
        "cold": (f"Hi — I lead AI governance audit coverage at a major investment bank (CPA, NIST AI "
                 f"RMF / EU AI Act work). I'm genuinely interested in {role} at {company} and would "
                 f"value 15 minutes of your perspective on the team."),
        "recruiter": (f"Hi — Director-level internal auditor at a major investment bank, specializing in "
                      f"AI governance / AI risk (CPA, AIGP in progress). Actively exploring senior "
                      f"manager/director {role}. Happy to share my resume if useful for your searches."),
    }
    follow_up = (f"Thanks for connecting! Quick context: 10 yrs in banking internal audit, now leading "
                 f"AI governance framework reviews (NIST AI RMF / EU AI Act / ISO 42001) and presenting "
                 f"to senior leadership. If a referral or intro for the {role} opening makes sense, "
                 f"I'd really appreciate it — and happy to make it easy with a tailored resume.")
    return {"connection_note": openers.get(relationship, openers["cold"]), "follow_up": follow_up}


# ---------------- recruiter pipeline ----------------

def recruiter_pipeline(today: dt.date | None = None) -> dict:
    """Who's due for a touch + this week's new-connection plan."""
    cfg = _load(RECRUITERS_PATH)
    today = today or dt.date.today()
    cadence = int(cfg.get("cadence_days", 30))
    due, active = [], 0
    for c in cfg.get("contacts", []) or []:
        last = c.get("last_contact")
        if isinstance(last, str):
            try:
                last = dt.date.fromisoformat(last)
            except ValueError:
                last = None
        active += 1
        if last is None or (today - last).days >= cadence:
            due.append({**c, "days_since": (today - last).days if last else None})

    firms = cfg.get("target_firms", []) or []
    # rotate through target firms by ISO week so every week suggests fresh ones
    week = today.isocalendar()[1]
    n = int(cfg.get("weekly_new_target", 7))
    picks = [firms[(week * 3 + i) % len(firms)] for i in range(min(3, len(firms)))] if firms else []
    plan = []
    for f in picks:
        plan.append({
            "firm": f["name"], "focus": f.get("focus", ""),
            "url": _li_people(f'"{f["name"]}" recruiter ("internal audit" OR "AI governance" OR risk)'),
        })
    plan.append({
        "firm": "目标公司内部 recruiter", "focus": "看今日 Top Jobs 对应公司",
        "url": _li_people('recruiter "AI governance"'),
    })
    return {"due": due, "weekly_target": n, "weekly_plan": plan, "total_contacts": active,
            "opener": outreach_drafts("your target companies", relationship="recruiter")["connection_note"]}


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--company")
    ap.add_argument("--title", default="")
    ap.add_argument("--recruiters", action="store_true")
    args = ap.parse_args()

    if args.recruiters:
        p = recruiter_pipeline()
        print(f"Recruiter pipeline: {p['total_contacts']} 个关系，{len(p['due'])} 个到期该跟进")
        for d in p["due"]:
            print(f"  · {d.get('name')} ({d.get('firm')}) — {d.get('days_since', '?')} 天没联系")
        print(f"\n本周新增计划（目标 {p['weekly_target']} 个）:")
        for x in p["weekly_plan"]:
            print(f"  + {x['firm']} — {x['focus']}\n    {x['url']}")
        print(f"\n通用破冰消息:\n  {p['opener']}")
        return

    if not args.company:
        print("用法: python -m src.network --company 'Citi' [--title '...']  或 --recruiters")
        return
    links = links_for_company(args.company)
    for section, items in links.items():
        if items:
            print(f"\n[{section}]")
            for it in items:
                print(f"  {it['label']}\n    {it['url']}")
    drafts = outreach_drafts(args.company, args.title)
    print(f"\n[connection note 草稿]\n  {drafts['connection_note']}")
    print(f"\n[连接后跟进草稿]\n  {drafts['follow_up']}")


if __name__ == "__main__":
    main()
