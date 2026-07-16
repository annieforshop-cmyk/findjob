"""Render the daily shortlist as plain text + HTML for email."""
from __future__ import annotations

import html
from datetime import date

from .sources.base import Job


def _fmt_matched(job: Job) -> str:
    return ", ".join(job.matched[:8]) if job.matched else "—"


def build_text(jobs: list[Job], meta: dict) -> str:
    lines = [
        f"findjob — 每日岗位精选  {date.today().isoformat()}",
        f"扫描 {meta.get('scanned', '?')} 个岗位，匹配 {len(jobs)} 个（阈值 {meta.get('min_score')}）",
        "=" * 60,
        "",
    ]
    for i, j in enumerate(jobs, 1):
        lines += [
            f"{i}. [{j.score:.0f}分] {j.title} — {j.company}",
            f"    来源 {j.source} | {j.location or 'Remote'}",
            f"    命中技能: {_fmt_matched(j)}",
        ]
        if j.missing:
            lines.append(f"    JD 还提到（你可考虑如实补充）: {', '.join(j.missing[:6])}")
        lines += [f"    {j.url}", ""]
    if not jobs:
        lines.append("今天没有达到阈值的新岗位。可以调低 config.yaml 的 min_score 或放宽 skills。")
    return "\n".join(lines)


def build_html(jobs: list[Job], meta: dict) -> str:
    def esc(s: str) -> str:
        return html.escape(s or "")

    rows = []
    for i, j in enumerate(jobs, 1):
        missing = (
            f'<div style="color:#a15c00;font-size:12px;margin-top:4px">JD 提到 · 可如实补充：{esc(", ".join(j.missing[:6]))}</div>'
            if j.missing
            else ""
        )
        rows.append(
            f"""
        <tr>
          <td style="padding:14px 12px;border-bottom:1px solid #eee;vertical-align:top">
            <div style="display:inline-block;min-width:42px;text-align:center;background:#0b6;color:#fff;
                        border-radius:6px;padding:3px 8px;font-weight:700;font-size:13px">{j.score:.0f}</div>
          </td>
          <td style="padding:14px 12px;border-bottom:1px solid #eee">
            <a href="{esc(j.url)}" style="font-size:15px;font-weight:600;color:#0a58ca;text-decoration:none">{esc(j.title)}</a>
            <div style="color:#444;font-size:13px;margin-top:2px">{esc(j.company)} · {esc(j.location or 'Remote')} · <span style="color:#888">{esc(j.source)}</span></div>
            <div style="color:#1a7f37;font-size:12px;margin-top:4px">命中：{esc(_fmt_matched(j))}</div>
            {missing}
          </td>
        </tr>"""
        )

    body = "".join(rows) or (
        '<tr><td style="padding:20px;color:#666">今天没有达到阈值的新岗位。'
        "可调低 config.yaml 的 min_score 或放宽 skills。</td></tr>"
    )
    return f"""<!doctype html><html><body style="margin:0;background:#f6f7f9;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">
    <div style="max-width:680px;margin:0 auto;padding:24px 16px">
      <h1 style="font-size:20px;margin:0 0 4px">findjob · 每日岗位精选</h1>
      <div style="color:#666;font-size:13px;margin-bottom:16px">{date.today().isoformat()} ·
        扫描 {meta.get('scanned','?')} 个 → 匹配 {len(jobs)} 个（阈值 {meta.get('min_score')}）</div>
      <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:10px;overflow:hidden">
        {body}
      </table>
      <div style="color:#999;font-size:12px;margin-top:16px">
        想改方向/技能/阈值？编辑仓库里的 <code>config.yaml</code>。<br>
        想为某个岗位生成简历对齐 + cover letter：<code>python -m src.tailor "岗位序号或链接"</code>
      </div>
    </div></body></html>"""
