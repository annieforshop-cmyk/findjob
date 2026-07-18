"""Personal Branding — one LinkedIn post draft per week, in your voice.

Topics rotate through an AI-governance editorial calendar (config `branding:`).
Drafts are grounded in the resume + story library — real practitioner takes,
not AI fluff. The Monday Career Brief embeds the draft; you edit 20% and post.

State (last topic index / history) lives in data/branding/state.json.

CLI:  python -m src.branding            # this week's draft
      python -m src.branding --topic "EU AI Act enforcement"
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

from . import stories

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "data" / "branding" / "state.json"

DEFAULT_TOPICS = [
    "NIST AI RMF 在银行内审中的实际落地——从框架到审计程序",
    "EU AI Act 对美国金融机构的实际影响：该准备什么",
    "内部审计如何审 GenAI 用例：一个 practitioner 的清单",
    "AI onboarding/intake 到持续监控：治理闭环最常断在哪",
    "Agentic AI 进入审计工作流：机会、边界与控制",
    "ISO/IEC 42001 vs NIST AI RMF：什么时候用哪个",
    "向高管讲 AI 风险：把监管语言翻译成业务决策语言",
    "三道防线在 AI 治理中的分工——以及为什么经常失灵",
    "Model risk 与 AI governance 的交界：MRM 团队教我的事",
    "从内审转型 AI 治理：这条路的真实样子",
]

SYSTEM = """You ghost-write LinkedIn posts for a real senior internal-audit /
AI-governance practitioner at a major bank. Hard rules:
1. TRUTH ONLY — ground claims in the resume/stories provided; no invented
   projects, clients, or numbers. General industry observations are fine.
2. PRACTITIONER VOICE — specific, opinionated, first-person, plain language.
   No "I'm thrilled", no emoji walls, no engagement-bait, no hashtags spam
   (max 3 at the end). 150-250 words. Short paragraphs. One concrete takeaway.
3. Never mention the employer by name — say "at a large investment bank"."""

USER_TMPL = """TOPIC THIS WEEK: {topic}

AUTHOR'S REAL BACKGROUND (resume excerpt):
\"\"\"{resume}\"\"\"

AUTHOR'S REAL WORK STORIES (may reference obliquely, no confidential details):
{stories}

Write ONE LinkedIn post (150-250 words) + a one-line comment the author can
pin under it inviting discussion. Format:
POST:
<post text>
PINNED COMMENT:
<comment>"""


def _state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:
            pass
    return {"topic_idx": 0, "history": []}


def _save_state(s: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(s, ensure_ascii=False, indent=1))


def next_topic(cfg: dict | None = None) -> tuple[str, int]:
    topics = ((cfg or {}).get("branding", {}) or {}).get("topics") or DEFAULT_TOPICS
    s = _state()
    idx = s.get("topic_idx", 0) % len(topics)
    return topics[idx], idx


def generate(topic: str | None = None, cfg: dict | None = None, advance: bool = True) -> str | None:
    """Weekly post draft; None if no LLM key."""
    try:
        from openai import OpenAI
    except ImportError:
        return None
    if not os.environ.get("OPENAI_API_KEY"):
        return None

    idx = None
    if not topic:
        topic, idx = next_topic(cfg)

    resume_p = ROOT / "profiles" / "ai-governance" / "resume.md"
    resume = resume_p.read_text() if resume_p.exists() else ""
    sel = stories.select(topic, k=2)

    client = OpenAI()
    try:
        resp = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER_TMPL.format(
                    topic=topic, resume=resume[:3000],
                    stories=stories.as_prompt_block(sel, 2500))},
            ],
        )
    except Exception as e:
        print(f"  branding: draft failed: {e}", file=sys.stderr)
        return None
    draft = f"【本周话题】{topic}\n\n{resp.choices[0].message.content}"

    if advance and idx is not None:
        s = _state()
        s["topic_idx"] = idx + 1
        s.setdefault("history", []).append({"date": dt.date.today().isoformat(), "topic": topic})
        s["history"] = s["history"][-30:]
        _save_state(s)
    return draft


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic")
    args = ap.parse_args()
    out = generate(args.topic, advance=not args.topic)
    if not out:
        sys.exit("需要 OPENAI_API_KEY（pip install openai）")
    print(out)


if __name__ == "__main__":
    main()
