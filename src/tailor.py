"""Per-job assistant: ATS keyword alignment + a cover letter draft.

Grounded in profile/resume.md — it will NOT invent experience. It only:
  1) flags which JD keywords your resume already supports (and how to phrase
     them to match the JD's wording), and which it doesn't;
  2) drafts a sincere, natural, professional cover letter from real material.

Usage:
  python -m src.tailor 3                 # 3rd job from the last daily run
  python -m src.tailor "https://..."     # by URL
  python -m src.tailor --title "Data Scientist" --company "Acme" \
      --desc "paste the JD here"

Needs OPENAI_API_KEY. Model via OPENAI_MODEL (default gpt-4o).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import store

ROOT = Path(__file__).resolve().parent.parent

SYSTEM = """You are helping a real job seeker apply. Two hard rules:
1. TRUTH ONLY. Use exclusively facts present in the candidate's resume. Never
   invent employers, titles, dates, metrics, tools, or achievements. If the job
   asks for something the resume doesn't support, say so plainly — do not fake it.
2. HUMAN VOICE. Write the way a thoughtful person writes: plain, specific,
   warm, confident. No AI throat-clearing, no "I am excited to apply", no
   "passionate about leveraging synergies", no purple adjectives, no em-dash
   pileups. Short varied sentences. Concrete over generic.

For ATS: the goal is honest keyword alignment — where the candidate genuinely
has a skill but phrased it differently than the JD, suggest matching the JD's
exact wording. Never suggest claiming a skill they lack."""

USER_TMPL = """CANDIDATE RESUME (the only source of truth about them):
\"\"\"
{resume}
\"\"\"

TARGET JOB
Title: {title}
Company: {company}
Description:
\"\"\"
{desc}
\"\"\"

Produce three sections in Markdown:

## 1. ATS 关键词对齐
A table of the JD's important keywords/skills. For each: Present in resume?
(yes / no / partial) and, if yes/partial, the exact phrasing to use so it
matches the JD. Then 2-4 concrete, truthful resume-bullet rewrites that align
existing experience to this JD's language (keep every number real).

## 2. 缺口
Skills the JD wants that the resume genuinely does not show. Honest list, plus
whether each is worth a quick upskilling note or should just be left alone.

## 3. Cover Letter
A ready-to-send cover letter (about 200-280 words). Sincere and specific to THIS
company/role, grounded only in the resume. Open with a real reason this role
fits — not "I am excited". Pick 1-2 genuine highlights that map to the JD. Sound
like a person, not a template."""


def _pick_job(args) -> dict:
    if args.desc:
        return {"title": args.title or "(untitled)", "company": args.company or "", "description": args.desc}
    runs = store.load_last_run()
    if not runs:
        sys.exit("没有 data/last_run.json；先跑 `python -m src.main` 或用 --desc 手动传入 JD。")
    sel = args.selector
    if sel and sel.isdigit():
        idx = int(sel) - 1
        if not (0 <= idx < len(runs)):
            sys.exit(f"序号超出范围（1-{len(runs)}）。")
        return runs[idx]
    if sel:  # match by url substring
        for j in runs:
            if sel in j.get("url", ""):
                return j
        sys.exit("没找到匹配该链接的岗位。")
    return runs[0]


def generate(resume: str, job: dict) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("请先 `pip install openai`。")
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("未设置 OPENAI_API_KEY。")

    client = OpenAI()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    prompt = USER_TMPL.format(
        resume=resume.strip() or "(resume is empty — fill profile/resume.md)",
        title=job.get("title", ""),
        company=job.get("company", ""),
        desc=(job.get("description", "") or "")[:6000],
    )
    resp = client.chat.completions.create(
        model=model,
        temperature=0.6,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("selector", nargs="?", help="last-run 序号 或 URL 子串")
    ap.add_argument("--title")
    ap.add_argument("--company")
    ap.add_argument("--desc", help="直接粘贴 JD 文本")
    ap.add_argument("-o", "--out", help="写入文件（默认打印到屏幕）")
    args = ap.parse_args()

    resume = (ROOT / "profile" / "resume.md").read_text()
    job = _pick_job(args)
    print(f"→ 生成中：{job.get('title')} @ {job.get('company')}", file=sys.stderr)
    out = generate(resume, job)

    if args.out:
        Path(args.out).write_text(out, encoding="utf-8")
        print(f"已写入 {args.out}", file=sys.stderr)
    else:
        print("\n" + out)


if __name__ == "__main__":
    main()
