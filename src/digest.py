"""Render the daily shortlist as plain text + HTML for email."""
from __future__ import annotations

import html
from datetime import date

from .sources.base import Job


def _fmt_matched(job: Job) -> str:
    return ", ".join(job.matched[:8]) if job.matched else "—"


def _score_label(meta: dict) -> str:
    return "AI匹配分" if meta.get("used_ai") else "关键词分"


_REC_ZH = {"apply": "建议投", "maybe": "可考虑", "skip": "可跳过"}
_GHOST_ZH = {"low": "低", "medium": "中", "high": "高"}


def build_text(jobs: list[Job], meta: dict, tailored: dict[str, str] | None = None) -> str:
    tailored = tailored or {}
    lines = [
        f"findjob · {meta.get('label','')} — 每日岗位精选  {date.today().isoformat()}",
        f"扫描 {meta.get('scanned', '?')} 个岗位，匹配 {len(jobs)} 个（{_score_label(meta)}，阈值 {meta.get('min_score')}）",
        "=" * 60,
        "",
    ]
    for i, j in enumerate(jobs, 1):
        rec = _REC_ZH.get(j.ai_recommendation, "")
        head = f"{i}. [{j.rank_score:.0f}分] {j.title} — {j.company}"
        if rec:
            head += f"  〈{rec}〉"
        lines.append(head)
        lines.append(f"    来源 {j.source} | {j.ai_location_note or j.location or 'Remote'}")
        if j.description:
            d = j.description.strip()
            lines.append(f"    内容: {d[:219] + '…' if len(d) > 220 else d}")
        if j.ai_special:
            lines.append(f"    ⚡ 特别注意: {j.ai_special}")
        if j.ai_reason:
            lines.append(f"    匹配理由: {j.ai_reason}")
            lines.append(f"    技能 {j.ai_skills:.0f} · 职级 {j.ai_seniority:.0f} · 年限 {j.ai_years_fit:.0f}")
        extras = []
        if j.ai_salary:
            extras.append(f"薪资 {j.ai_salary}")
        if j.ai_ghost_risk:
            extras.append(f"幽灵岗风险 {_GHOST_ZH.get(j.ai_ghost_risk, j.ai_ghost_risk)}")
        if extras:
            lines.append("    " + " | ".join(extras))
        if j.ai_company_note:
            lines.append(f"    公司: {j.ai_company_note}")
        if j.matched:
            lines.append(f"    命中技能: {_fmt_matched(j)}")
        if j.missing:
            lines.append(f"    缺口（可如实补充）: {', '.join(j.missing[:6])}")
        lines.append(f"    {j.url}")
        if j.id in tailored:
            lines.append("    --- 已为你预写 cover letter 草稿 ---")
            lines.append("\n".join("    " + ln for ln in tailored[j.id].splitlines()))
        lines.append("")
    if not jobs:
        lines.append("今天没有达到阈值的新岗位。可以调低 profile 的 min_score 或放宽 skills。")
    return "\n".join(lines)


def build_html(jobs: list[Job], meta: dict, tailored: dict[str, str] | None = None) -> str:
    tailored = tailored or {}

    def esc(s: str) -> str:
        return html.escape(s or "")

    def chip(text: str, bg: str, fg: str = "#fff") -> str:
        return (
            f'<span style="display:inline-block;background:{bg};color:{fg};border-radius:5px;'
            f'padding:2px 7px;font-size:11px;font-weight:600;margin-right:6px">{esc(text)}</span>'
        )

    rows = []
    for i, j in enumerate(jobs, 1):
        rec_bg = {"apply": "#0b6", "maybe": "#c58", "skip": "#999"}.get(j.ai_recommendation, "")
        rec = chip(_REC_ZH.get(j.ai_recommendation, ""), rec_bg) if rec_bg else ""

        meters = ""
        if j.ai_reason:
            meters = (
                f'<div style="color:#333;font-size:13px;margin-top:5px">💡 {esc(j.ai_reason)}</div>'
                f'<div style="color:#666;font-size:12px;margin-top:3px">'
                f'技能 <b>{j.ai_skills:.0f}</b> · 职级 <b>{j.ai_seniority:.0f}</b> · 年限 <b>{j.ai_years_fit:.0f}</b></div>'
            )

        facts = []
        if j.ai_salary:
            facts.append(chip(f"💰 {j.ai_salary}", "#eef", "#334"))
        if j.ai_ghost_risk:
            gbg = {"low": "#e7f6ec", "medium": "#fff4e0", "high": "#fde8e8"}.get(j.ai_ghost_risk, "#eee")
            gfg = {"low": "#1a7f37", "medium": "#a15c00", "high": "#c02"}.get(j.ai_ghost_risk, "#333")
            facts.append(chip(f"👻 幽灵岗 {_GHOST_ZH.get(j.ai_ghost_risk, '')}", gbg, gfg))
        facts_html = f'<div style="margin-top:6px">{"".join(facts)}</div>' if facts else ""

        company = (
            f'<div style="color:#555;font-size:12px;margin-top:4px">🏢 {esc(j.ai_company_note)}</div>'
            if j.ai_company_note else ""
        )
        matched = (
            f'<div style="color:#1a7f37;font-size:12px;margin-top:4px">命中：{esc(_fmt_matched(j))}</div>'
            if j.matched else ""
        )
        missing = (
            f'<div style="color:#a15c00;font-size:12px;margin-top:4px">缺口 · 可如实补充：{esc(", ".join(j.missing[:6]))}</div>'
            if j.missing else ""
        )
        draft = ""
        if j.id in tailored:
            draft = (
                '<details style="margin-top:8px"><summary style="cursor:pointer;color:#7b2ff7;font-size:12px;font-weight:600">'
                '📄 已预写 cover letter 草稿（点开）</summary>'
                f'<pre style="white-space:pre-wrap;background:#faf7ff;border:1px solid #eadcff;border-radius:8px;'
                f'padding:10px;font-size:12px;margin-top:6px">{esc(tailored[j.id])}</pre></details>'
            )
        loc = esc(j.ai_location_note or j.location or "Remote")
        d = (j.description or "").strip()
        snippet = (
            f'<div style="color:#555;font-size:12.5px;margin-top:4px">{esc(d[:219] + "…" if len(d) > 220 else d)}</div>'
            if d else ""
        )
        if j.ai_special:
            snippet += (f'<div style="background:#fffbe6;border:1px solid #f0e0a0;border-radius:6px;'
                        f'padding:5px 8px;font-size:12.5px;color:#7a5c00;margin-top:5px">'
                        f'⚡ {esc(j.ai_special)}</div>')
        rows.append(
            f"""
        <tr>
          <td style="padding:14px 12px;border-bottom:1px solid #eee;vertical-align:top">
            <div style="display:inline-block;min-width:42px;text-align:center;background:#0b6;color:#fff;
                        border-radius:6px;padding:3px 8px;font-weight:700;font-size:13px">{j.rank_score:.0f}</div>
          </td>
          <td style="padding:14px 12px;border-bottom:1px solid #eee">
            <div>{rec}<a href="{esc(j.url)}" style="font-size:15px;font-weight:600;color:#0a58ca;text-decoration:none">{esc(j.title)}</a></div>
            <div style="color:#444;font-size:13px;margin-top:2px">{esc(j.company)} · {loc} · <span style="color:#888">{esc(j.source)}</span></div>
            {snippet}{meters}{facts_html}{company}{matched}{missing}{draft}
          </td>
        </tr>"""
        )

    body = "".join(rows) or (
        '<tr><td style="padding:20px;color:#666">今天没有达到阈值的新岗位。'
        "可调低 profile 的 min_score 或放宽 skills。</td></tr>"
    )
    return f"""<!doctype html><html><body style="margin:0;background:#f6f7f9;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
    <div style="max-width:700px;margin:0 auto;padding:24px 16px">
      <h1 style="font-size:20px;margin:0 0 4px">findjob · {esc(meta.get('label',''))} · 每日岗位精选</h1>
      <div style="color:#666;font-size:13px;margin-bottom:16px">{date.today().isoformat()} ·
        扫描 {meta.get('scanned','?')} 个 → 匹配 {len(jobs)} 个 · {_score_label(meta)}（阈值 {meta.get('min_score')}）</div>
      <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden">
        {body}
      </table>
      <div style="color:#999;font-size:12px;margin-top:16px">
        方向/技能/搜索词在 <code>profiles/{esc(meta.get('label',''))}/profile.yaml</code>。<br>
        为某岗位生成简历对齐 + cover letter：<code>python -m src.tailor --profile &lt;方向&gt; &lt;序号&gt;</code>
      </div>
    </div></body></html>"""
