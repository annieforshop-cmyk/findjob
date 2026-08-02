"""Daily Job Feed — ONE email: the new, high-fit jobs on the market today.

Deliberately narrow: no target-firm list, no networking, no company research.
Just today's fresh postings across every enabled source, merged across all
career directions, deduped, and filtered to a high score floor so what lands
in your inbox is worth opening.

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

from . import ai_score, notify_email, store
from .main import collect_profile, discover_profiles
from .sources.base import Job

ROOT = Path(__file__).resolve().parent.parent

# 交叉岗专属板块，永远排在邮件最前面（见 profile.yaml 的 combo_boost）
COMBO_SECTION = "🔥 AI × 审计 交叉岗"


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
    # score floor for what makes it into the feed. Only high-confidence
    # matches — the whole point is precision, not volume.
    floor = float(base_cfg.get("min_score", 60))

    merged: dict[str, Job] = {}
    scanned = 0
    ai_notes: list[str] = []
    section_order: list[str] = []      # 板块展示顺序（按 config 里 profile 出现顺序）
    # which directions feed today's email (default: all discovered)
    wanted = bcfg.get("profiles")
    names = [p for p in discover_profiles() if not wanted or p in wanted] or discover_profiles()
    for name in names:
        try:
            res = collect_profile(name, dry_run)
        except Exception as e:
            print(f"  brief: profile {name} failed: {e}", file=sys.stderr)
            continue
        scanned += res["meta"].get("scanned", 0)
        if res["meta"].get("ai_note"):
            ai_notes.append(res["meta"]["ai_note"])
        section = res["cfg"].get("section") or res["label"]  # 多个 profile 可共享一个板块
        if section not in section_order:
            section_order.append(section)
        fresh = [j for j in res["top"] if j.rank_score >= floor]
        if not fresh:
            # 这个方向今天一个新岗都没有。AI 治理是个小市场，很多天确实
            # 就是零——但整块从邮件里消失，看起来像"这个方向坏了"。
            # 所以退回展示上一次跑出来的存量岗，明确标成"不是新岗"。
            fresh = _still_open(name, floor, int(bcfg.get("fallback_per_section", 5)))
            for j in fresh:
                j.stale = True          # type: ignore[attr-defined]
        for j in fresh:
            j.profile_label = res["label"]  # type: ignore[attr-defined]
            # 交叉岗（AI × 审计）单独成块并置顶：这类岗同时要 AI 和审计两边，
            # 正好卡在你的独特画像上，市面上极少，混在普通岗里会被淹掉。
            j.section = COMBO_SECTION if j.combo else section  # type: ignore[attr-defined]
            old = merged.get(j.id)
            if old is None or j.rank_score > old.rank_score:
                merged[j.id] = j

    jobs = [j for j in merged.values() if j.rank_score >= floor]
    jobs.sort(key=lambda j: -j.rank_score)
    # collapse the same role posted at multiple locations (same title+company,
    # different URLs) into one line — keep the highest-scored, note the count
    by_role: dict[tuple, Job] = {}
    for j in jobs:
        key = ((j.title or "").strip().lower(), (j.company or "").strip().lower())
        if key not in by_role:
            j.dupe_count = 1  # type: ignore[attr-defined]
            by_role[key] = j
        else:
            by_role[key].dupe_count = getattr(by_role[key], "dupe_count", 1) + 1  # type: ignore[attr-defined]
    jobs = list(by_role.values())
    jobs = _cap_per_company(jobs, int(bcfg.get("per_company_cap", 3)))
    top = _select(jobs, bcfg)

    return {"date": today, "scanned": scanned, "top": top, "floor": floor,
            "cfg": base_cfg, "section_order": section_order,
            "ai_warning": "；".join(dict.fromkeys(ai_notes))}


def _still_open(ns: str, floor: float, n: int) -> list[Job]:
    """某个方向今天没有新岗时的兜底：上次跑出来的高分存量岗。

    这些岗你之前的邮件里见过，所以会明确标 `stale`，渲染成「仍在招 · 不是新岗」，
    不会让你误以为是今天新出的。
    """
    if n <= 0:
        return []
    out: list[Job] = []
    for d in store.load_last_run(ns):
        try:
            j = Job(**{k: v for k, v in d.items()
                       if k in Job.__dataclass_fields__})
        except Exception:
            continue
        if j.rank_score >= floor:
            out.append(j)
    out.sort(key=lambda j: -j.rank_score)
    return out[:n]


def _select(jobs: list[Job], bcfg: dict) -> list[Job]:
    """挑进邮件的岗位。**先给每个方向留保底名额，再用剩下的名额按分排。**

    为什么不是简单取全局前 50：三个方向的分数分布不一样（内部审计岗多、
    命中词多，分数普遍顶到 100；AI 治理是个小市场，好岗也就 90 出头）。
    全局排序一截断，AI 治理整块就被挤没了——邮件看起来像"只有内部审计"。

    保底按 **profile_label（方向）** 分，不是按 section（板块）：
    ai-governance 和 ai-risk 共用"AI 治理 & 风险"这一个板块，按板块分配的话
    ai-risk 照样能把 ai-governance 挤光，等于没修。
    """
    limit = int(bcfg.get("top_jobs", 50))
    floor_per = int(bcfg.get("min_per_section", 8))

    def key(j: Job):
        # 交叉岗（AI × 审计）永远排在最前面——这类岗最贴你的画像，且极少见
        return (0 if getattr(j, "combo", "") else 1, -j.rank_score)

    jobs = sorted(jobs, key=key)
    picked: list[Job] = []
    used: set[str] = set()

    if floor_per > 0:
        by_dir: dict[str, list[Job]] = {}
        for j in jobs:
            by_dir.setdefault(getattr(j, "profile_label", "") or "", []).append(j)
        for dir_jobs in by_dir.values():
            for j in dir_jobs[:floor_per]:
                picked.append(j)
                used.add(j.id)

    for j in jobs:                       # 剩下的名额全局按分补齐
        if len(picked) >= limit:
            break
        if j.id not in used:
            picked.append(j)
            used.add(j.id)

    # picked 的规模已经被上面两步限住了（保底名额 + 补齐到 limit）。
    # 保底名额总数超过 limit 时以保底为准——保证每个方向都在，是这里的第一优先。
    return sorted(picked, key=key)


# ---------------- render helpers ----------------

def _dims(j: Job) -> str:
    if j.ai_composite < 0:
        return ""
    bits = [f"综合 {j.ai_composite:.0f}"]
    if j.ai_skills >= 0:
        bits.append(f"技能 {j.ai_skills:.0f}")
    if j.ai_seniority >= 0:
        bits.append(f"职级 {j.ai_seniority:.0f}")
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
    d = (j.description or "").strip()
    return (d[: n - 1] + "…") if len(d) > n else d


def _why(j: Job) -> str:
    if j.ai_reason:
        return j.ai_reason
    if j.matched:
        return "命中你简历的关键词: " + ", ".join(j.matched[:8])
    return ""


def _sections_in_order(d: dict) -> list[str]:
    order = list(d.get("section_order") or [])
    for j in d["top"]:                      # 兜底：把任何漏掉的板块补到末尾
        s = getattr(j, "section", "") or ""
        if s and s not in order:
            order.append(s)
    if COMBO_SECTION in order:              # 交叉岗永远第一块
        order = [COMBO_SECTION] + [s for s in order if s != COMBO_SECTION]
    return order


def _source_label(j: Job) -> str:
    """人话来源：ats:BlackRock -> 'BlackRock 官网直连'，其余（The Muse /
    'LinkedIn (via JSearch)' / RemoteOK …）原样显示。"""
    s = (getattr(j, "source", "") or "").strip()
    if s.startswith("ats:"):
        return f"{s[4:]} 官网直连"
    return s


# ---------------- render: text ----------------

def _job_lines(i: int, j: Job) -> list[str]:
    label = getattr(j, "profile_label", "")
    n = getattr(j, "dupe_count", 1)
    lines = [f"{i}. [{j.rank_score:.0f}] "
             + (f"🔥[{j.combo}] " if getattr(j, "combo", "") else "")
             + f"{j.title} — {j.company}"
             + (f"  〈{label}〉" if label else "")
             + ("  (仍在招 · 不是今天新岗)" if getattr(j, "stale", False) else "")
             + (f"  (+{n - 1} 个其他地点)" if n > 1 else "")]
    lines.append(f"   {j.ai_location_note or j.location or 'Remote'}"
                 + (f" | {j.ai_salary}" if j.ai_salary else "")
                 + (f" | 发布 {j.posted}" if j.posted else "")
                 + (f" | 来源 {_source_label(j)}" if j.source else ""))
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
    L = [f"每日新岗 · {d['date'].isoformat()}",
         f"扫描 {d['scanned']} 个岗位 → {len(d['top'])} 个达标（≥{d['floor']:.0f} 分）",
         "=" * 62, ""]

    if d.get("ai_warning"):
        L += [f"⚠️ AI 语义打分今天没有正常运行：{d['ai_warning']}",
              "   排序退化为关键词匹配，达标数量可能偏少——修好后会明显回升。", ""]

    if d["top"]:
        i = 0
        for sec in _sections_in_order(d):
            secjobs = [j for j in d["top"] if getattr(j, "section", "") == sec]
            if not secjobs:
                continue
            L += [f"━━━━━ {sec}（{len(secjobs)} 个）━━━━━", ""]
            for j in secjobs:
                i += 1
                L += _job_lines(i, j) + [""]
    else:
        L.append("今天没有达标（≥60 分）的新岗位。宁缺毋滥——明天再看。\n")

    L.append("-" * 62)
    L.append("投某个岗位：python -m src.tailor --profile <方向> \"<岗位链接或JD>\"  生成对齐+cover letter")
    L.append("记录投递：python -m src.track apply \"公司\" \"岗位\"")
    return "\n".join(L)


# ---------------- render: html ----------------

def _chip(text: str, bg: str, fg: str = "#fff") -> str:
    return (f'<span style="display:inline-block;background:{bg};color:{fg};border-radius:5px;'
            f'padding:2px 7px;font-size:11px;font-weight:600;margin:0 6px 4px 0">{esc(text)}</span>')


def _job_html(j: Job) -> str:
    label = getattr(j, "profile_label", "")
    chips = []
    if j.ai_composite >= 0:
        for name, v in (("技能", j.ai_skills), ("职级", j.ai_seniority),
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
    if j.posted:
        chips.append(_chip(f"📅 {j.posted}", "#eef7ee", "#1a5c2e"))
    if j.source:
        chips.append(_chip(f"🔗 {_source_label(j)}", "#eef", "#345"))
    snip = _snippet(j)
    desc = (f'<div style="color:#555;font-size:12.5px;margin-top:4px">{esc(snip)}</div>'
            if snip else "")
    why = _why(j)
    reason = (f'<div style="color:#333;font-size:13px;margin-top:4px">💡 {esc(why)}</div>'
              if why else "")
    special = (f'<div style="background:#fffbe6;border:1px solid #f0e0a0;border-radius:6px;'
               f'padding:5px 8px;font-size:12.5px;color:#7a5c00;margin-top:5px">'
               f'⚡ {esc(j.ai_special)}</div>' if j.ai_special else "")
    return f"""<tr>
      <td style="padding:12px;border-bottom:1px solid #eee;vertical-align:top;width:46px">
        <div style="text-align:center;background:#0b6;color:#fff;border-radius:6px;
                    padding:3px 8px;font-weight:700;font-size:13px">{j.rank_score:.0f}</div></td>
      <td style="padding:12px;border-bottom:1px solid #eee">
        <div>{(_chip(f"🔥 {j.combo}", "#ffece0", "#b03a00") if getattr(j, "combo", "") else "")}
             <a href="{esc(j.url)}" style="font-size:15px;font-weight:600;color:#0a58ca;
             text-decoration:none">{esc(j.title)}</a>
             {(_chip(label, "#e8eef7", "#245") if label else "")}
             {(_chip("仍在招 · 非新岗", "#f4f4f4", "#666") if getattr(j, "stale", False) else "")}
             {(_chip(f"+{getattr(j,'dupe_count',1)-1} 地点", "#eee", "#555") if getattr(j,'dupe_count',1) > 1 else "")}</div>
        <div style="color:#444;font-size:13px;margin-top:2px">{esc(j.company)} ·
             {esc(j.ai_location_note or j.location or 'Remote')}</div>
        {desc}{special}{reason}<div style="margin-top:5px">{''.join(chips)}</div>
      </td></tr>"""


def build_html(d: dict) -> str:
    warning = ""
    if d.get("ai_warning"):
        warning = (
            '<div style="background:#fff4e0;border:1px solid #f0c36d;border-radius:8px;'
            'padding:10px 14px;margin:14px 0;font-size:13px;color:#7a4b00">'
            f'⚠️ <b>AI 语义打分今天没有正常运行</b>：{esc(d["ai_warning"])}<br>'
            '排序退化为关键词匹配，达标数量可能偏少——修好后会明显回升。</div>')

    if d["top"]:
        blocks = []
        for sec in _sections_in_order(d):
            secjobs = [j for j in d["top"] if getattr(j, "section", "") == sec]
            if not secjobs:
                continue
            rows = "".join(_job_html(j) for j in secjobs)
            blocks.append(
                f'<h2 style="font-size:15px;margin:22px 0 8px;color:#111">{esc(sec)}'
                f'<span style="color:#888;font-weight:400;font-size:13px"> · {len(secjobs)} 个</span></h2>'
                f'<table style="width:100%;border-collapse:collapse;background:#fff;'
                f'border-radius:10px;overflow:hidden">{rows}</table>')
        body = "".join(blocks)
    else:
        body = ('<div style="background:#fff;border-radius:10px;padding:20px;color:#555;'
                'font-size:14px">今天没有达标（≥60 分）的新岗位。宁缺毋滥——明天再看。</div>')

    return f"""<!doctype html><html><body style="margin:0;background:#f6f7f9;
    font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
    <div style="max-width:700px;margin:0 auto;padding:24px 16px">
      <h1 style="font-size:20px;margin:0">📬 每日新岗 · {d['date'].isoformat()}</h1>
      <div style="color:#666;font-size:13px;margin:4px 0 6px">扫描 {d['scanned']} 个岗位 →
        {len(d['top'])} 个达标（≥{d['floor']:.0f} 分）· 只推高匹配，宁缺毋滥</div>
      {warning}
      {body}
      <div style="color:#999;font-size:12px;margin-top:18px">
        <code>python -m src.tailor --profile &lt;方向&gt; "&lt;链接或JD&gt;"</code> 生成对齐+cover letter ·
        <code>python -m src.track apply "公司" "岗位"</code> 记录投递
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

    if not d["top"]:
        print("  brief: 今天没有达标新岗位；跳过邮件", file=sys.stderr)
        return 0
    subject = f"📬 每日新岗 {d['date'].isoformat()} · {len(d['top'])} 个高匹配"
    notify_email.send(subject, text, build_html(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
