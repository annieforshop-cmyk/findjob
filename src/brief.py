"""Daily Career Brief — ONE email, 20-30 minutes of focused action a day.

Consolidates everything the system knows into a single morning brief:
  ⭐ Dream-company new postings (direct ATS monitoring, Target-50 list)
  🎯 Top jobs across ALL profiles, ranked by composite Fit Score v2
  🔎 Company research hooks for the top picks (news + LLM synthesis)
  🤝 Networking: exactly who to contact for the top jobs (alumni/ex-colleagues/DMs)
  ⏰ Follow-ups due on in-flight applications
  📇 Recruiter pipeline: who's due for a touch + Monday's new-connection plan
  ✍️ Monday: this week's LinkedIn post draft

Run:  python -m src.brief            # full run + email
      python -m src.brief --dry-run  # print only
"""
from __future__ import annotations

import argparse
import datetime as dt
import html as html_mod
import sys
from pathlib import Path

import yaml

from . import ai_score, branding, dream, network, notify_email, research, track
from .main import collect_profile, discover_profiles
from .sources.base import Job

ROOT = Path(__file__).resolve().parent.parent


def esc(s: str) -> str:
    return html_mod.escape(str(s or ""))


# ---------------- gather ----------------

def _cap_per_company(jobs: list[Job], cap: int) -> list[Job]:
    """同一家公司最多保留 cap 个岗位，避免任何一家刷屏。"""
    if cap <= 0:
        return jobs
    counts: dict[str, int] = {}
    out = []
    for j in jobs:
        key = (j.company or "?").strip().lower()
        counts[key] = counts.get(key, 0) + 1
        if counts[key] <= cap:
            out.append(j)
    return out


def gather(dry_run: bool) -> dict:
    base_cfg = yaml.safe_load((ROOT / "config.yaml").read_text()) or {}
    bcfg = base_cfg.get("brief", {}) or {}
    today = dt.date.today()

    # 1. all profiles
    merged: dict[str, Job] = {}
    tailored: dict[str, str] = {}
    scanned = 0
    for name in discover_profiles():
        try:
            res = collect_profile(name, dry_run)
        except Exception as e:
            print(f"  brief: profile {name} failed: {e}", file=sys.stderr)
            continue
        scanned += res["meta"].get("scanned", 0)
        tailored.update(res["tailored"])
        for j in res["top"]:
            j.profile_label = res["label"]  # type: ignore[attr-defined]
            old = merged.get(j.id)
            if old is None or j.rank_score > old.rank_score:
                merged[j.id] = j

    # 2. dream-company channel 1: direct ATS postings, AI-scored vs primary profile
    dream_jobs: list[Job] = []
    try:
        fresh = dream.fetch_new(mark_seen=not dry_run)
        applied = track.applied_index()
        if applied:
            fresh = [j for j in fresh if not track.is_applied(j, applied)]
        fresh = fresh[: int(bcfg.get("dream_max", 15))]
        if fresh:
            primary = bcfg.get("primary_profile", "ai-governance")
            try:
                from .main import load_context
                pcfg, presume, _, _ = load_context(primary)
                fresh, _ = ai_score.rescore(fresh, presume, pcfg)
            except Exception as e:
                print(f"  brief: dream scoring skipped: {e}", file=sys.stderr)
            dream_jobs = sorted([j for j in fresh if j.ai_location_ok],
                                key=lambda j: (j.dream_tier, -j.rank_score))
            dream_jobs = _cap_per_company(dream_jobs, int(bcfg.get("dream_per_company", 3)))
    except Exception as e:
        print(f"  brief: dream channel failed: {e}", file=sys.stderr)

    jobs = list(merged.values())
    n_agency = network.flag_agencies(jobs)
    if n_agency:
        print(f"  brief: {n_agency} postings are recruiter/agency jobs (🎯 direct line to a recruiter)",
              file=sys.stderr)
    # 按分数排序：dream 只加小额加分，不再无条件置顶（防止单一公司刷屏）
    jobs.sort(key=lambda j: -(j.rank_score + (3 if j.dream else 0)))
    jobs = _cap_per_company(jobs, int(bcfg.get("per_company_cap", 3)))
    top_n = int(bcfg.get("top_jobs", 50))
    top = jobs[:top_n]

    # 3. research the strongest picks (cached 14d, so cheap)
    briefs = []
    seen_companies = set()
    for j in (dream_jobs[:2] + top):
        c = (j.company or "").strip()
        if not c or c.lower() in seen_companies:
            continue
        seen_companies.add(c.lower())
        if len(briefs) >= int(bcfg.get("research_top", 3)):
            break
        b = research.brief(c, j.title)
        if b:
            briefs.append(b)

    # 4. networking for top picks
    net_top = []
    for j in (dream_jobs[:2] + top)[: int(bcfg.get("networking_top", 4))]:
        links = network.links_for_company(j.company)
        picks = (links["alumni"][:1] + links["ex_colleagues"][:1]
                 + links["decision_makers"][:2] + links["recruiters"][:1])
        net_top.append({"job": j, "links": picks,
                        "note": network.outreach_drafts(j.company, j.title)["connection_note"]})

    # 5. follow-ups + recruiter pipeline
    followups = track.followups_due(today)
    pipeline = network.recruiter_pipeline(today)
    is_monday = today.weekday() == int(bcfg.get("weekly_day", 0))

    # 6. Monday: LinkedIn draft
    post = branding.generate(cfg=base_cfg, advance=not dry_run) if is_monday else None

    return {"date": today, "scanned": scanned, "top": top, "dream": dream_jobs,
            "tailored": tailored, "research": briefs, "networking": net_top,
            "followups": followups, "pipeline": pipeline, "is_monday": is_monday,
            "post": post, "cfg": base_cfg}


# ---------------- render: text ----------------

def _dims(j: Job) -> str:
    if j.ai_composite < 0:
        return ""
    bits = [f"综合 {j.ai_composite:.0f}"]
    if j.ai_gov >= 0:
        bits.append(f"AI治理 {j.ai_gov:.0f}")
    if j.ai_career >= 0:
        bits.append(f"职业路径 {j.ai_career:.0f}")
    if j.ai_recruiter_odds >= 0:
        bits.append(f"回复概率 {j.ai_recruiter_odds:.0f}")
    if j.ai_stability:
        bits.append(f"稳定性风险 {j.ai_stability}")
    if j.ai_work_mode:
        bits.append({"remote": "🏠 Remote", "hybrid": "Hybrid",
                     "onsite": "Onsite"}.get(j.ai_work_mode, j.ai_work_mode))
    if j.embed_sim >= 0:
        bits.append(f"语义相似 {j.embed_sim:.0f}")
    return " · ".join(bits)


def _snippet(j: Job, n: int = 220) -> str:
    """JD 内容缩略：让邮件里能看出这岗位到底是干什么的。"""
    d = (j.description or "").strip()
    return (d[: n - 1] + "…") if len(d) > n else d


def _why(j: Job) -> str:
    """推荐理由：优先 LLM 理由；没有 LLM 时退回到命中的简历关键词，绝不留空。"""
    if j.ai_reason:
        return j.ai_reason
    if j.matched:
        return "命中你简历的关键词: " + ", ".join(j.matched[:8])
    return ""


def _job_lines(i: int, j: Job) -> list[str]:
    star = ("⭐" if j.dream else "") + ("🎯" if j.agency else "")
    label = getattr(j, "profile_label", "")
    lines = [f"{i}. {star}[{j.rank_score:.0f}] {j.title} — {j.company}"
             + (f"  〈{label}〉" if label else "")]
    if j.agency:
        lines.append("   🎯 猎头代招岗——投递即进入该猎头数据库；投完顺手在 LinkedIn 连接发帖 recruiter")
    lines.append(f"   {j.ai_location_note or j.location or 'Remote'}"
                 + (f" | {j.ai_salary}" if j.ai_salary else ""))
    snip = _snippet(j)
    if snip:
        lines.append(f"   内容: {snip}")
    if j.ai_special:
        lines.append(f"   ⚡ 特别注意: {j.ai_special}")
    why = _why(j)
    if why:
        lines.append(f"   💡 {why}")
    d = _dims(j)
    if d:
        lines.append(f"   {d}")
    lines.append(f"   {j.url}")
    return lines


def build_text(d: dict) -> str:
    L = [f"Career Brief · {d['date'].isoformat()}",
         f"扫描 {d['scanned']} 个岗位 → 精选 {len(d['top'])} | Dream 新岗 {len(d['dream'])}"
         f" | 待跟进 {len(d['followups'])}",
         "=" * 62, ""]

    if d["dream"]:
        L.append("⭐ DREAM COMPANY 官网新岗位")
        for i, j in enumerate(d["dream"], 1):
            L += _job_lines(i, j) + [""]

    L.append("🎯 今日 TOP JOBS（综合 Fit Score 排序）")
    if d["top"]:
        for i, j in enumerate(d["top"], 1):
            L += _job_lines(i, j) + [""]
    else:
        L.append("  今天没有达标新岗位——把时间花在 networking 上。\n")

    if d["followups"]:
        L.append("⏰ 今日必须跟进")
        for f in d["followups"]:
            L.append(f"  {f['action']}")
            L.append(f"    {f.get('company')} — {f.get('title')}")
        L.append("")

    p = d["pipeline"]
    L.append(f"📇 RECRUITER PIPELINE（{p['total_contacts']} 个关系，{len(p['due'])} 个到期）")
    for c in p["due"][:5]:
        L.append(f"  · 该联系 {c.get('name')} ({c.get('firm')}) — {c.get('days_since', '?')} 天未触达")
    if d["is_monday"]:
        L.append(f"  本周新增目标 {p['weekly_target']} 个，从这里开始：")
        for x in p["weekly_plan"]:
            L.append(f"  + {x['firm']} — {x['focus']}\n    {x['url']}")
    L.append("")

    if d["networking"]:
        L.append("🤝 为 TOP 岗位找内推（点链接就是精准人选）")
        for n in d["networking"]:
            j = n["job"]
            L.append(f"  ▸ {j.company} — {j.title}")
            for lk in n["links"]:
                L.append(f"    {lk['label']}: {lk['url']}")
        L.append("")

    for b in d["research"]:
        L.append(research.render_text(b))
        L.append("")

    if d["post"]:
        L.append("✍️ 本周 LinkedIn 内容（编辑 20% 后发布）")
        L.append(d["post"])
        L.append("")

    L.append("-" * 62)
    L.append("今日 20-30 分钟动作清单：投 Top 1-3 → 每岗位发 1-2 条内推触达 → 处理跟进项"
             + ("→ 发 LinkedIn 帖" if d["post"] else ""))
    L.append("记录: python -m src.track apply/status/recruiter · 面试: python -m src.interview")
    return "\n".join(L)


# ---------------- render: html ----------------

def _chip(text: str, bg: str, fg: str = "#fff") -> str:
    return (f'<span style="display:inline-block;background:{bg};color:{fg};border-radius:5px;'
            f'padding:2px 7px;font-size:11px;font-weight:600;margin:0 6px 4px 0">{esc(text)}</span>')


def _job_html(j: Job, tailored: dict[str, str]) -> str:
    star = ("⭐ " if j.dream else "") + ("🎯 " if j.agency else "")
    label = getattr(j, "profile_label", "")
    chips = []
    if j.agency:
        chips.append(_chip("🎯 猎头代招 — 投递=进猎头库", "#fde68a", "#78350f"))
    if j.ai_composite >= 0:
        for name, v in (("AI治理", j.ai_gov), ("职业路径", j.ai_career),
                        ("行业", j.ai_industry), ("回复概率", j.ai_recruiter_odds)):
            if v >= 0:
                chips.append(_chip(f"{name} {v:.0f}", "#eef", "#334"))
    if j.ai_stability:
        sbg = {"low": "#e7f6ec", "medium": "#fff4e0", "high": "#fde8e8"}.get(j.ai_stability, "#eee")
        sfg = {"low": "#1a7f37", "medium": "#a15c00", "high": "#c02"}.get(j.ai_stability, "#333")
        chips.append(_chip(f"裁员风险 {j.ai_stability}", sbg, sfg))
    if j.ai_work_mode:
        wlabel = {"remote": "🏠 Remote", "hybrid": "Hybrid", "onsite": "Onsite"}.get(j.ai_work_mode)
        if wlabel:
            wbg = {"remote": "#e7f6ec", "hybrid": "#fff4e0", "onsite": "#f4f4f4"}[j.ai_work_mode]
            wfg = {"remote": "#1a7f37", "hybrid": "#a15c00", "onsite": "#555"}[j.ai_work_mode]
            chips.append(_chip(wlabel, wbg, wfg))
    if j.ai_salary:
        chips.append(_chip(f"💰 {j.ai_salary}", "#f3f0ff", "#5b21b6"))
    snip = _snippet(j)
    desc = (f'<div style="color:#555;font-size:12.5px;margin-top:4px">{esc(snip)}</div>'
            if snip else "")
    why = _why(j)
    reason = (f'<div style="color:#333;font-size:13px;margin-top:4px">💡 {esc(why)}</div>'
              if why else "")
    special = (f'<div style="background:#fffbe6;border:1px solid #f0e0a0;border-radius:6px;'
               f'padding:5px 8px;font-size:12.5px;color:#7a5c00;margin-top:5px">'
               f'⚡ {esc(j.ai_special)}</div>' if j.ai_special else "")
    draft = ""
    if j.id in tailored:
        draft = ('<details style="margin-top:6px"><summary style="cursor:pointer;color:#7b2ff7;'
                 'font-size:12px;font-weight:600">📄 cover letter 草稿</summary>'
                 f'<pre style="white-space:pre-wrap;background:#faf7ff;border:1px solid #eadcff;'
                 f'border-radius:8px;padding:10px;font-size:12px">{esc(tailored[j.id])}</pre></details>')
    return f"""<tr>
      <td style="padding:12px;border-bottom:1px solid #eee;vertical-align:top;width:46px">
        <div style="text-align:center;background:{'#c78500' if j.dream else '#0b6'};color:#fff;border-radius:6px;
                    padding:3px 8px;font-weight:700;font-size:13px">{j.rank_score:.0f}</div></td>
      <td style="padding:12px;border-bottom:1px solid #eee">
        <div>{star}<a href="{esc(j.url)}" style="font-size:15px;font-weight:600;color:#0a58ca;
             text-decoration:none">{esc(j.title)}</a>
             {(_chip(label, "#e8eef7", "#245") if label else "")}</div>
        <div style="color:#444;font-size:13px;margin-top:2px">{esc(j.company)} ·
             {esc(j.ai_location_note or j.location or 'Remote')}</div>
        {desc}{special}{reason}<div style="margin-top:5px">{''.join(chips)}</div>{draft}
      </td></tr>"""


def _section(title: str, inner: str) -> str:
    return (f'<h2 style="font-size:15px;margin:22px 0 8px;color:#111">{title}</h2>'
            f'<table style="width:100%;border-collapse:collapse;background:#fff;'
            f'border-radius:10px;overflow:hidden">{inner}</table>')


def _row(inner: str) -> str:
    return f'<tr><td style="padding:10px 12px;border-bottom:1px solid #f0f0f0;font-size:13px">{inner}</td></tr>'


def build_html(d: dict) -> str:
    parts = []
    if d["dream"]:
        parts.append(_section("⭐ Dream Company 官网新岗位",
                              "".join(_job_html(j, d["tailored"]) for j in d["dream"])))
    parts.append(_section("🎯 今日 Top Jobs（综合 Fit Score）",
                          "".join(_job_html(j, d["tailored"]) for j in d["top"])
                          or _row("今天没有达标新岗位——把时间花在下面的 networking 上。")))

    if d["followups"]:
        rows = "".join(_row(f"<b>{esc(f.get('company'))}</b> — {esc(f.get('title'))}<br>"
                            f"<span style='color:#a15c00'>{esc(f['action'])}</span>")
                       for f in d["followups"])
        parts.append(_section("⏰ 今日必须跟进", rows))

    p = d["pipeline"]
    rows = []
    for c in p["due"][:5]:
        li = c.get("linkedin", "")
        link = f' — <a href="{esc(li)}">LinkedIn</a>' if li else ""
        rows.append(_row(f"该联系 <b>{esc(c.get('name'))}</b> ({esc(c.get('firm'))}) · "
                         f"{c.get('days_since', '?')} 天未触达{link}"))
    if d["is_monday"]:
        rows.append(_row(f"<b>本周新增 recruiter 连接目标：{p['weekly_target']} 个</b>"))
        for x in p["weekly_plan"]:
            rows.append(_row(f'<a href="{esc(x["url"])}">{esc(x["firm"])}</a> — {esc(x["focus"])}'))
    if not rows:
        rows.append(_row(f"pipeline 有 {p['total_contacts']} 个关系，今天没有到期项 ✓"))
    parts.append(_section("📇 Recruiter Pipeline", "".join(rows)))

    if d["networking"]:
        rows = []
        for n in d["networking"]:
            j = n["job"]
            links = " · ".join(f'<a href="{esc(lk["url"])}">{esc(lk["label"])}</a>' for lk in n["links"])
            rows.append(_row(f"<b>{esc(j.company)}</b> — {esc(j.title)}<br>{links}<br>"
                             f'<span style="color:#666">破冰: {esc(n["note"])}</span>'))
        parts.append(_section("🤝 为 Top 岗位找内推", "".join(rows)))

    if d["research"]:
        rows = []
        for b in d["research"]:
            body = esc(research.render_text(b)).replace("\n", "<br>")
            rows.append(_row(f'<details><summary style="cursor:pointer;font-weight:600">'
                             f'🔎 {esc(b.get("company"))} 尽调（裁员风险: {esc(b.get("layoff_risk", "?"))}）'
                             f'</summary><div style="margin-top:6px;color:#333">{body}</div></details>'))
        parts.append(_section("🔎 公司研究", "".join(rows)))

    if d["post"]:
        parts.append(_section("✍️ 本周 LinkedIn 内容（编辑后发布）",
                              _row(f'<pre style="white-space:pre-wrap;font-size:12px;margin:0">{esc(d["post"])}</pre>')))

    return f"""<!doctype html><html><body style="margin:0;background:#f6f7f9;
    font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
    <div style="max-width:700px;margin:0 auto;padding:24px 16px">
      <h1 style="font-size:20px;margin:0">🧭 Career Brief · {d['date'].isoformat()}</h1>
      <div style="color:#666;font-size:13px;margin:4px 0 6px">扫描 {d['scanned']} → 精选 {len(d['top'])}
        · Dream 新岗 {len(d['dream'])} · 跟进 {len(d['followups'])} · 今日预算 20-30 分钟</div>
      {''.join(parts)}
      <div style="color:#999;font-size:12px;margin-top:18px">
        动作清单：投 Top 1-3 → 每岗 1-2 条内推触达 → 跟进项 → {'发 LinkedIn 帖 → ' if d['post'] else ''}收工。<br>
        <code>python -m src.track apply "公司" "岗位"</code> 记录投递 ·
        <code>python -m src.interview prep --company X</code> 面试准备
      </div>
    </div></body></html>"""


# ---------------- entry ----------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    d = gather(args.dry_run)
    text = build_text(d)
    print(text)
    if args.dry_run:
        print("\n(dry-run: 未发邮件)", file=sys.stderr)
        return 0

    has_content = d["top"] or d["dream"] or d["followups"] or d["pipeline"]["due"] or d["post"]
    if not has_content:
        print("  brief: nothing actionable today; skipping email", file=sys.stderr)
        return 0
    subject = (f"🧭 Career Brief {d['date'].isoformat()} · Top {len(d['top'])}"
               + (f" · ⭐Dream {len(d['dream'])}" if d["dream"] else "")
               + (f" · 跟进 {len(d['followups'])}" if d["followups"] else ""))
    notify_email.send(subject, text, build_html(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
