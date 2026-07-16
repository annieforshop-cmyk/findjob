"""Stage-2: LLM as a comprehensive, multi-dimensional job analyst.

Keyword overlap (score.py) is a cheap wide net. This stage reads each job's
DESCRIPTION (not its title) and judges fit across many dimensions for THIS
specific candidate, returning structured output the email can explain:

  overall / skills / seniority / years fit · location check · salary ·
  ghost-job risk · company note · recommendation · gap skills

It is told the candidate's real profile (level, years, work authorization,
location flexibility) so it can, e.g., treat a "Director" title realistically
against a senior-manager-level candidate, and accept any US location.

Cost control: runs only on keyword pre-filter survivors (capped), batched,
truncated JDs. Degrades gracefully to keyword scores with no key / on failure.
"""
from __future__ import annotations

import json
import os
import sys

from .sources.base import Job

BATCH = 4
JD_CHARS = 1900

SYSTEM = """You are a senior career analyst evaluating job fit for one specific
candidate. Judge the ACTUAL WORK in each job description, never the title alone
(titles are inconsistent across companies). Be rigorous and honest — do not
inflate scores, and do not invent facts about a company you don't know.
Return ONLY valid JSON."""

USER_TMPL = """CANDIDATE PROFILE:
{candidate}

CANDIDATE RESUME (source of truth on skills/experience):
\"\"\"
{resume}
\"\"\"

Analyze each job for THIS candidate and return JSON:
{{"results": [
  {{"id": "<job id>",
    "overall": <0-100 overall fit, weighing content > title>,
    "skills_fit": <0-100 skill/domain overlap with the described work>,
    "seniority_fit": <0-100 how well the ROLE'S real level matches the candidate's
        real band (senior manager to director/VP); a title of 'Director' that is
        really an IC, or a 'VP' needing 20 yrs, should score lower>,
    "years_fit": <0-100 fit vs the candidate's ~10 yrs total / ~8 yrs bank
        internal audit; roles wanting far more or far less score lower>,
    "location_ok": <true if the role can be done from a US location the candidate
        accepts — remote, hybrid, or onsite ANYWHERE in the US. If the JD lists
        multiple locations and any is in the US, true. Non-US-only => false>,
    "location_note": "<brief: e.g. 'Remote US' / 'Hybrid NYC' / 'Onsite Dallas or Remote' / 'London only'>",
    "salary": "<pay range from the JD if stated, else a realistic US market estimate for this role+level, e.g. '$180k-230k (est.)'>",
    "ghost_risk": "<low|medium|high — high if JD is vague/generic, evergreen, or a likely repost>",
    "company_note": "<one clause of known context/reputation if you genuinely know the company; else ''>",
    "reason": "<=20 words, concrete reason for the overall score",
    "recommendation": "<apply|maybe|skip>",
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


def _candidate_ctx(cfg: dict) -> str:
    c = cfg.get("candidate", {}) or {}
    if c.get("summary"):
        return c["summary"]
    return "Experienced professional; judge by resume."


def _score_batch(client, model: str, candidate: str, resume: str, batch: list[Job]) -> dict[str, dict]:
    payload = [
        {"id": j.id, "title": j.title, "company": j.company,
         "location": j.location, "description": (j.description or "")[:JD_CHARS]}
        for j in batch
    ]
    resp = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER_TMPL.format(
                candidate=candidate,
                resume=resume.strip()[:6000] or "(empty resume)",
                jobs=json.dumps(payload, ensure_ascii=False),
            )},
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    return {r["id"]: r for r in data.get("results", []) if "id" in r}


def _apply(job: Job, r: dict) -> None:
    job.ai_score = float(r.get("overall", 0))
    job.ai_skills = float(r.get("skills_fit", 0))
    job.ai_seniority = float(r.get("seniority_fit", 0))
    job.ai_years_fit = float(r.get("years_fit", 0))
    job.ai_reason = str(r.get("reason", ""))[:200]
    job.ai_recommendation = str(r.get("recommendation", "")).lower()[:10]
    job.ai_location_ok = bool(r.get("location_ok", True))
    job.ai_location_note = str(r.get("location_note", ""))[:80]
    job.ai_salary = str(r.get("salary", ""))[:60]
    job.ai_ghost_risk = str(r.get("ghost_risk", "")).lower()[:10]
    job.ai_company_note = str(r.get("company_note", ""))[:160]
    if r.get("missing"):
        job.missing = [str(m) for m in r["missing"]][:8]


def rescore(jobs: list[Job], resume: str, cfg: dict) -> tuple[list[Job], bool]:
    """Attach multi-dimensional LLM analysis. Returns (jobs, used_ai)."""
    acfg = cfg.get("ai_scoring", {}) or {}
    if not acfg.get("enabled", False):
        return jobs, False
    client = _client()
    if client is None:
        print("  ai_scoring enabled but no OPENAI_API_KEY/openai — using keyword scores", file=sys.stderr)
        return jobs, False

    model = acfg.get("model", "gpt-4o-mini")
    candidate = _candidate_ctx(cfg)
    used = False
    for i in range(0, len(jobs), BATCH):
        batch = jobs[i:i + BATCH]
        try:
            scored = _score_batch(client, model, candidate, resume, batch)
        except Exception as e:
            print(f"  ai batch {i // BATCH} failed: {e}", file=sys.stderr)
            continue
        for j in batch:
            r = scored.get(j.id)
            if r:
                used = True
                _apply(j, r)
    print(f"  ai analyzed {sum(1 for j in jobs if j.ai_reason)} jobs", file=sys.stderr)
    return jobs, used
