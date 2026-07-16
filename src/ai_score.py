"""Stage-2 scoring: LLM semantic fit, structured output.

Keyword overlap (score.py) is a cheap, wide net. This module takes the
survivors and asks an LLM to judge *actual* fit between the job's described work
and the candidate's resume — catching matches the JD phrases differently, and
penalising title-only "matches". It returns a structured score + a one-line
reason so the email can explain itself.

Cost control: runs only on the keyword pre-filter survivors (capped), batched,
with truncated JDs. Degrades gracefully — if there's no OPENAI_API_KEY or the
call fails, jobs keep their keyword score and the pipeline still ships.
"""
from __future__ import annotations

import json
import os
import sys

from .sources.base import Job

BATCH = 6
JD_CHARS = 1600

SYSTEM = """You rank how well a job fits a specific candidate, judging the actual
WORK described — not the title. Reward genuine overlap in responsibilities,
tools, and seniority even when the job phrases things differently from the
resume. Penalise jobs that only share a title but need different work. Be
skeptical and honest; do not inflate. Output ONLY valid JSON, no prose."""

USER_TMPL = """CANDIDATE RESUME:
\"\"\"
{resume}
\"\"\"

Score each job below for THIS candidate. Return a JSON object:
{{"results": [
  {{"id": "<job id>",
    "overall": <0-100 overall fit>,
    "skills_fit": <0-100>,
    "experience_fit": <0-100>,
    "reason": "<=18 words, concrete reason for the score",
    "missing": ["skills the job needs that the resume lacks"]}}
]}}
Include one entry per job id. JOBS:
{jobs}"""


def _client():
    try:
        from openai import OpenAI
    except ImportError:
        return None
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    return OpenAI()


def _score_batch(client, model: str, resume: str, batch: list[Job]) -> dict[str, dict]:
    jobs_payload = [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "description": (j.description or "")[:JD_CHARS],
        }
        for j in batch
    ]
    resp = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER_TMPL.format(
                resume=resume.strip()[:6000] or "(empty resume)",
                jobs=json.dumps(jobs_payload, ensure_ascii=False),
            )},
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    return {r["id"]: r for r in data.get("results", []) if "id" in r}


def rescore(jobs: list[Job], resume: str, cfg: dict) -> tuple[list[Job], bool]:
    """Attach LLM fit to each job. Returns (jobs, used_ai)."""
    acfg = cfg.get("ai_scoring", {}) or {}
    if not acfg.get("enabled", False):
        return jobs, False
    client = _client()
    if client is None:
        print("  ai_scoring enabled but no OPENAI_API_KEY/openai — using keyword scores", file=sys.stderr)
        return jobs, False

    model = acfg.get("model", "gpt-4o-mini")
    used = False
    for i in range(0, len(jobs), BATCH):
        batch = jobs[i:i + BATCH]
        try:
            scored = _score_batch(client, model, resume, batch)
        except Exception as e:
            print(f"  ai batch {i // BATCH} failed: {e}", file=sys.stderr)
            continue
        for j in batch:
            r = scored.get(j.id)
            if not r:
                continue
            used = True
            j.ai_score = float(r.get("overall", 0))
            j.ai_skills = float(r.get("skills_fit", 0))
            j.ai_experience = float(r.get("experience_fit", 0))
            j.ai_reason = str(r.get("reason", ""))[:160]
            if r.get("missing"):
                j.missing = [str(m) for m in r["missing"]][:8]
    print(f"  ai scored {sum(1 for j in jobs if j.ai_score >= 0 and j.ai_reason)} jobs", file=sys.stderr)
    return jobs, used
