"""Tracker CLI — applications & recruiter contacts, with follow-up logic.

  python -m src.track apply "Citi" "Director, AI Governance" --url https://... --via referral
  python -m src.track status "Citi" interviewing
  python -m src.track recruiter "Jane Doe" --firm "Selby Jennings" --note "..."
  python -m src.track touch "Jane Doe"          # 记录今天联系过了
  python -m src.track list                      # 全部在途申请 + 跟进状态

Follow-up rules (surfaced in the daily Career Brief):
  applied + 7d  no response -> follow-up #1 (message recruiter/HM)
  applied + 14d no response -> follow-up #2 or route to networking
  interviewing              -> prep reminder (src.interview prep)
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
APPS_PATH = ROOT / "career" / "applications.yaml"
RECRUITERS_PATH = ROOT / "career" / "recruiters.yaml"

FOLLOW_1, FOLLOW_2 = 7, 14
STALE = 45  # 45 天无响应视为沉没，不再提醒


def _load(path: Path) -> dict:
    if path.exists():
        return yaml.safe_load(path.read_text()) or {}
    return {}


def _dump(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))


def _date(v) -> dt.date | None:
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str):
        try:
            return dt.date.fromisoformat(v[:10])
        except ValueError:
            return None
    return None


def applied_index() -> list[dict]:
    """所有已记录过的申请（不论 applied/interviewing/offer/rejected）——
    这些岗位不应再出现在每日推荐里。"""
    out = []
    for a in _load(APPS_PATH).get("applications", []) or []:
        out.append({
            "company": (a.get("company") or "").lower().strip(),
            "title": (a.get("title") or "").lower().strip(),
            "url": (a.get("url") or "").strip(),
        })
    return out


def is_applied(job, idx: list[dict] | None = None) -> bool:
    """岗位是否已投过：URL 精确匹配，或 公司匹配+职位词重合≥60%（模糊容错）。"""
    idx = applied_index() if idx is None else idx
    if not idx:
        return False
    comp = (job.company or "").lower().strip()
    title_words = set((job.title or "").lower().split())
    url = (job.url or "").strip()
    for a in idx:
        if a["url"] and url and a["url"] == url:
            return True
        if not a["company"] or not comp:
            continue
        if a["company"] in comp or comp in a["company"]:
            aw = set(a["title"].split())
            if aw and title_words and len(aw & title_words) / len(aw) >= 0.6:
                return True
    return False


def followups_due(today: dt.date | None = None) -> list[dict]:
    """Applications that need action today."""
    today = today or dt.date.today()
    out = []
    for a in _load(APPS_PATH).get("applications", []) or []:
        status = (a.get("status") or "applied").lower()
        applied = _date(a.get("applied"))
        if status == "interviewing":
            out.append({**a, "action": "🎤 有面试在途 — 跑 interview prep + 复盘上一轮"})
            continue
        if status not in ("applied", "followed-up") or not applied:
            continue
        days = (today - applied).days
        if days >= STALE:
            continue
        if status == "applied" and days >= FOLLOW_1:
            out.append({**a, "action": f"⏰ 投递 {days} 天无回音 — follow-up #1：LinkedIn 上找 recruiter/HM 发消息"})
        elif status == "followed-up" and days >= FOLLOW_2:
            out.append({**a, "action": f"⏰ 已 {days} 天 — follow-up #2 或转 networking 找内推"})
    return out


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("apply")
    p.add_argument("company"); p.add_argument("title")
    p.add_argument("--url", default=""); p.add_argument("--via", default="direct")
    p.add_argument("--contact", default=""); p.add_argument("--note", default="")

    p = sub.add_parser("status")
    p.add_argument("company"); p.add_argument("new_status")

    p = sub.add_parser("recruiter")
    p.add_argument("name"); p.add_argument("--firm", default="")
    p.add_argument("--linkedin", default=""); p.add_argument("--note", default="")

    p = sub.add_parser("touch")
    p.add_argument("name")

    sub.add_parser("list")
    args = ap.parse_args()
    today = dt.date.today().isoformat()

    if args.cmd == "apply":
        data = _load(APPS_PATH)
        data.setdefault("applications", []).append({
            "company": args.company, "title": args.title, "url": args.url,
            "applied": today, "status": "applied", "via": args.via,
            "contact": args.contact, "notes": args.note,
        })
        _dump(APPS_PATH, data)
        print(f"已记录: {args.company} — {args.title} ({today})")

    elif args.cmd == "status":
        data = _load(APPS_PATH)
        hits = [a for a in data.get("applications", []) if args.company.lower() in a.get("company", "").lower()]
        if not hits:
            sys.exit(f"没找到公司包含 '{args.company}' 的申请")
        hits[-1]["status"] = args.new_status
        _dump(APPS_PATH, data)
        print(f"{hits[-1]['company']} — {hits[-1]['title']} → {args.new_status}")

    elif args.cmd == "recruiter":
        data = _load(RECRUITERS_PATH)
        data.setdefault("contacts", []).append({
            "name": args.name, "firm": args.firm, "linkedin": args.linkedin,
            "status": "connected", "last_contact": today, "notes": args.note,
        })
        _dump(RECRUITERS_PATH, data)
        print(f"已加入 recruiter pipeline: {args.name} ({args.firm})")

    elif args.cmd == "touch":
        data = _load(RECRUITERS_PATH)
        hits = [c for c in data.get("contacts", []) if args.name.lower() in c.get("name", "").lower()]
        if not hits:
            sys.exit(f"没找到 '{args.name}'")
        hits[-1]["last_contact"] = today
        _dump(RECRUITERS_PATH, data)
        print(f"{hits[-1]['name']} — last_contact = {today}")

    else:  # list
        apps = _load(APPS_PATH).get("applications", []) or []
        print(f"在途申请 {len(apps)} 个:")
        for a in apps:
            print(f"  [{a.get('status', '?')}] {a.get('company')} — {a.get('title')} (投于 {a.get('applied')})")
        due = followups_due()
        if due:
            print("\n今日需行动:")
            for d in due:
                print(f"  {d['action']}: {d.get('company')} — {d.get('title')}")


if __name__ == "__main__":
    main()
