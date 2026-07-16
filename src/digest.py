"""Render the daily shortlist as plain text + HTML for email."""
from __future__ import annotations

import html
from datetime import date

from .sources.base import Job


def _fmt_matched(job: Job) -> str:
    return ", ".join(job.matched[:8]) if job.matched else "—"


def _score_label(meta: dict) -> str:
    return "AI匹配分" if meta.get("used_ai") else "关键词分"


def build_text(jobs: list[Job], meta: dict, tailored: dict[str, str] | None = None) -> str:
    tailored = tailored or {}
    lines = [
        f"findjob · {meta.get('label','')} — 每日岗位精选  {date.today().isoformat()}",
        f"扫描 {meta.get('scanned', '?')} 个岗位，匹配 {len(jobs)} 个（{_score_label(meta)}，阈值 {meta.get('min_score')}）",
        "=" * 60,
        "",
    ]
    for i, j in enumerate(jobs, 1):
        lines.append(f"{i}. [{j.rank_score:.0f}分] {j.title} — {j.company}")
        lines.append(f"    来源 {j.source} | {j.location or 'Remote'}")
        if j.ai_reason:
            lines.append(f"    匹配理由: {j.ai_reason}")
            lines.append(f"    技能契合 {j.ai_skills:.0f} · 经历契合 {j.ai_experience:.0f}")
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
        lines.append("今天没有达到阈值的新岗位。可以调低 config.yaml 的 min_score 或放宽 skills。")
    return "\n".join(lines)


def build_html(jobs: list[Job], meta: dict, tailored: dict[str, str] | None = None) -> str:
    tailored = tailored or {}

    def esc(s: str) -> str:
        return html.escape(s or "")

    rows = []
    for i, j in enumerate(jobs, 1):
        reason = (
            f'<div style="color:#333;font-size:13px;margin-top:4px">💡 {esc(j.ai_reason)}'
            f'<span style="color:#888"> · 技能 {j.ai_skills:.0f} · 经历 {j.ai_experience:.0f}</span></div>'
            if j.ai_reason else ""
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
        rows.append(
            f"""
        <tr>
          <td style="padding:14px 12px;border-bottom:1px solid #eee;vertical-align:top">
            <div style="display:inline-block;min-width:42px;text-align:center;background:#0b6;color:#fff;
                        border-radius:6px;padding:3px 8px;font-weight:700;font-size:13px">{j.rank_score:.0f}</div>
          </td>
          <td style="padding:14px 12px;border-bottom:1px solid #eee">
            <a href="{esc(j.url)}" style="font-size:15px;font-weight:600;color:#0a58ca;text-decoration:none">{esc(j.title)}</a>
            <div style="color:#444;font-size:13px;margin-top:2px">{esc(j.company)} · {esc(j.location or 'Remote')} · <span style="color:#888">{esc(j.source)}</span></div>
            {reason}{matched}{missing}{draft}
          </td>
        </tr>"""
        )

    body = "".join(rows) or (
        '<tr><td style="padding:20px;color:#666">今天没有达到阈值的新岗位。'
        "可调低 config.yaml 的 min_score 或放宽 skills。</td></tr>"
    )
    return f"""<!doctype html><html><body style="margin:0;background:#f6f7f9;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
    <div style="max-width:680px;margin:0 auto;padding:24px 16px">
      <h1 style="font-size:20px;margin:0 0 4px">findjob · {esc(meta.get('label',''))} · 每日岗位精选</h1>
      <div style="color:#666;font-size:13px;margin-bottom:16px">{date.today().isoformat()} ·
        扫描 {meta.get('scanned','?')} 个 → 匹配 {len(jobs)} 个 · {_score_label(meta)}（阈值 {meta.get('min_score')}）</div>
      <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden">
        {body}
      </table>
      <div style="color:#999;font-size:12px;margin-top:16px">
        想改方向/技能/阈值？编辑仓库里的 <code>config.yaml</code>。<br>
        想为某个岗位生成简历对齐 + cover letter：<code>python -m src.tailor "岗位序号或链接"</code>
      </div>
    </div></body></html>"""
