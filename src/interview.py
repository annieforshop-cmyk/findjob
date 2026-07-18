"""Interview Knowledge Base — log every round, prep smarter every time.

  # 面试后 60 秒记录（questions 用 | 分隔）
  python -m src.interview log --company Citi --stage "HM round" \
      --interviewer "Jane D (MD, Audit)" \
      --questions "how do you audit GenAI|tell me about issue validation" \
      --notes "very NIST-focused; quantify dashboard story next time"

  # 面试前生成准备包：历史被问过的题 + 匹配的 STAR 故事 + 公司尽调 + 预测问题
  python -m src.interview prep --profile ai-governance --company Citi [selector]
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from pathlib import Path

from . import research, stories, store

ROOT = Path(__file__).resolve().parent.parent
KB_DIR = ROOT / "career" / "interviews"

PREP_SYSTEM = """You are an elite interview coach for a senior internal-audit /
AI-governance candidate. Ground everything in the provided resume and STAR
stories — never invent experience. Be specific and practical, not generic."""

PREP_TMPL = """CANDIDATE RESUME:
\"\"\"{resume}\"\"\"

CANDIDATE'S STAR STORY LIBRARY (their prepared material):
{stories}

TARGET: {title} at {company}
JOB DESCRIPTION:
\"\"\"{jd}\"\"\"

QUESTIONS THIS COMPANY ASKED IN PAST ROUNDS (from candidate's own interview log):
{past_questions}

COMPANY RESEARCH:
{research}

Produce a Markdown prep sheet:
## 1. 最可能被问的 10 个问题
Ranked; mark any repeats from past rounds with ⭐. Mix technical (AI governance,
NIST AI RMF, EU AI Act, model risk, audit methodology) and behavioral.
## 2. 每题的作答策略
One line each: which STAR story to use (by name) + the angle. If no story fits, say what truthful material to draw on.
## 3. 你该问面试官的 5 个问题
Sharp, informed by the company research — make the candidate look exceptionally prepared.
## 4. 风险点提醒
Where this candidate is weakest for THIS JD and how to honestly handle it."""


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _kb_path(company: str) -> Path:
    return KB_DIR / f"{_slug(company)}.md"


def log_round(company: str, stage: str, interviewer: str, questions: list[str],
              notes: str, role: str = "") -> Path:
    KB_DIR.mkdir(parents=True, exist_ok=True)
    p = _kb_path(company)
    if not p.exists():
        p.write_text(f"# {company} — Interview Log\n")
    entry = [f"\n---\n\n## {dt.date.today().isoformat()} — {stage}"]
    if role:
        entry.append(f"**岗位**: {role}")
    if interviewer:
        entry.append(f"**面试官**: {interviewer}")
    if questions:
        entry.append("**被问到的问题**")
        entry += [f"{i}. {q.strip()}" for i, q in enumerate(questions, 1)]
    if notes:
        entry.append(f"**笔记/反馈**\n{notes}")
    with p.open("a") as f:
        f.write("\n".join(entry) + "\n")
    return p


def past_questions(company: str) -> list[str]:
    p = _kb_path(company)
    if not p.exists():
        return []
    qs = []
    for line in p.read_text().splitlines():
        m = re.match(r"^\d+\.\s+(.+)", line.strip())
        if m:
            qs.append(m.group(1))
    return qs


def _find_job(company: str, selector: str | None, profile: str | None) -> dict:
    runs = store.load_last_run(profile or "default")
    if selector and selector.isdigit():
        idx = int(selector) - 1
        if 0 <= idx < len(runs):
            return runs[idx]
    for j in runs:
        if company.lower() in (j.get("company") or "").lower():
            return j
    return {"title": "", "company": company, "description": ""}


def prep(company: str, profile: str | None, selector: str | None) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("pip install openai")
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("需要 OPENAI_API_KEY")

    resume_p = ROOT / "profiles" / (profile or "ai-governance") / "resume.md"
    resume = resume_p.read_text() if resume_p.exists() else ""
    job = _find_job(company, selector, profile)
    jd = (job.get("description") or "")[:5000]
    sel = stories.select(jd or company, k=5)
    past = past_questions(company)
    rb = research.brief(company, job.get("title", "")) or {}

    client = OpenAI()
    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        temperature=0.4,
        messages=[
            {"role": "system", "content": PREP_SYSTEM},
            {"role": "user", "content": PREP_TMPL.format(
                resume=resume[:5000], stories=stories.as_prompt_block(sel),
                title=job.get("title") or "(unknown role)", company=company,
                jd=jd or "(JD not on file — prep generally for this company)",
                past_questions="\n".join(f"- {q}" for q in past) or "(none logged yet)",
                research=research.render_text(rb) or "(no research available)",
            )},
        ],
    )
    return resp.choices[0].message.content


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("log")
    p.add_argument("--company", required=True)
    p.add_argument("--stage", default="round")
    p.add_argument("--role", default="")
    p.add_argument("--interviewer", default="")
    p.add_argument("--questions", default="", help="多个问题用 | 分隔")
    p.add_argument("--notes", default="")

    p = sub.add_parser("prep")
    p.add_argument("selector", nargs="?", help="last-run 序号（可选）")
    p.add_argument("--company", required=True)
    p.add_argument("--profile", default="ai-governance")
    p.add_argument("-o", "--out")

    args = ap.parse_args()
    if args.cmd == "log":
        path = log_round(args.company, args.stage, args.interviewer,
                         [q for q in args.questions.split("|") if q.strip()],
                         args.notes, args.role)
        print(f"已记录 → {path}")
    else:
        out = prep(args.company, args.profile, args.selector)
        if args.out:
            Path(args.out).write_text(out)
            print(f"已写入 {args.out}")
        else:
            print(out)


if __name__ == "__main__":
    main()
