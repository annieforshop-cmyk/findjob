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

BATCH = 3  # more JSON per job in Fit Score v2 → smaller batches keep output reliable
JD_CHARS = 1900

SYSTEM = """You are a senior career analyst evaluating job fit for one specific
candidate. Judge the ACTUAL WORK in each job description, never the title alone
(titles are inconsistent across companies). Be rigorous and honest — do not
inflate scores, and do not invent facts about a company you don't know.
Return ONLY valid JSON."""

USER_TMPL = """CANDIDATE PROFILE:
{candidate}

CANDIDATE'S 3-5 YEAR CAREER GOAL (judge career_path_fit against THIS):
{career_goal}

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
    "industry_fit": <0-100 how well the employer's industry leverages the
        candidate's banking / financial-services / regulated-industry depth>,
    "leadership_fit": <0-100 does the role's people/program-leadership scope match
        someone who leads reviews, mentors staff, and presents to executives>,
    "ai_governance_fit": <0-100 how central AI governance / responsible AI /
        AI risk is to the described work (not just a buzzword mention)>,
    "growth_fit": <0-100 learning & growth upside: new scope, visibility,
        emerging-domain exposure vs a lateral repeat of what they already do>,
    "comp_fit": <0-100 likely comp attractiveness vs a senior-manager/director
        band in US financial services (~$180k+ base equivalent)>,
    "career_path_fit": <0-100 how much THIS role advances the stated 3-5 year
        goal — stepping-stone value, brand, scope trajectory — not just today's pay>,
    "stability": "<low|medium|high RISK — high if the company/sector has known
        layoffs, distress, or heavy role churn; low if stable/growing. If unknown, 'medium'>",
    "recruiter_odds": <0-100 realistic odds this application gets a recruiter
        response: penalize huge applicant pools, inflated requirements vs the
        candidate, stale posts; boost niche fits where the candidate is rare>,
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

# composite Fit Score weights — overridable via config `fit_weights:`
DEFAULT_WEIGHTS = {
    "overall": 0.20,
    "skills": 0.16,
    "seniority": 0.08,
    "industry": 0.10,
    "leadership": 0.06,
    "ai_governance": 0.10,
    "career_path": 0.12,
    "growth": 0.05,
    "comp": 0.05,
    "recruiter_odds": 0.08,
}
STABILITY_ADJ = {"low": +3.0, "medium": 0.0, "high": -8.0}  # low RISK is a bonus


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


def _career_goal(cfg: dict) -> str:
    goal = (cfg.get("career_goal") or "").strip()
    if goal:
        return goal
    return ("Grow into a Head / Director of AI Governance role at a major "
            "regulated institution within 3-5 years.")


def _score_batch(client, model: str, candidate: str, career_goal: str,
                 resume: str, batch: list[Job]) -> dict[str, dict]:
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
                career_goal=career_goal,
                resume=resume.strip()[:6000] or "(empty resume)",
                jobs=json.dumps(payload, ensure_ascii=False),
            )},
        ],
    )
    data = json.loads(resp.choices[0].message.content)
    return {r["id"]: r for r in data.get("results", []) if "id" in r}


def compute_composite(job: Job, weights: dict | None = None) -> float:
    """Weighted Fit Score from all scored dimensions + stability adjustment."""
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    parts = {
        "overall": job.ai_score,
        "skills": job.ai_skills,
        "seniority": job.ai_seniority,
        "industry": job.ai_industry,
        "leadership": job.ai_leadership,
        "ai_governance": job.ai_gov,
        "career_path": job.ai_career,
        "growth": job.ai_growth,
        "comp": job.ai_comp,
        "recruiter_odds": job.ai_recruiter_odds,
    }
    num = den = 0.0
    for k, v in parts.items():
        if v >= 0 and w.get(k, 0) > 0:
            num += w[k] * v
            den += w[k]
    if den == 0:
        return -1.0
    score = num / den + STABILITY_ADJ.get(job.ai_stability, 0.0)
    return max(0.0, min(100.0, score))


def _num(r: dict, key: str) -> float:
    try:
        return float(r.get(key, -1))
    except (TypeError, ValueError):
        return -1.0


def _apply(job: Job, r: dict, weights: dict | None = None) -> None:
    job.ai_score = float(r.get("overall", 0))
    job.ai_skills = float(r.get("skills_fit", 0))
    job.ai_seniority = float(r.get("seniority_fit", 0))
    job.ai_years_fit = float(r.get("years_fit", 0))
    job.ai_industry = _num(r, "industry_fit")
    job.ai_leadership = _num(r, "leadership_fit")
    job.ai_gov = _num(r, "ai_governance_fit")
    job.ai_growth = _num(r, "growth_fit")
    job.ai_comp = _num(r, "comp_fit")
    job.ai_career = _num(r, "career_path_fit")
    job.ai_stability = str(r.get("stability", "")).lower()[:10]
    job.ai_recruiter_odds = _num(r, "recruiter_odds")
    job.ai_composite = compute_composite(job, weights)
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
    career_goal = _career_goal(cfg)
    weights = cfg.get("fit_weights") or {}
    used = False
    for i in range(0, len(jobs), BATCH):
        batch = jobs[i:i + BATCH]
        try:
            scored = _score_batch(client, model, candidate, career_goal, resume, batch)
        except Exception as e:
            print(f"  ai batch {i // BATCH} failed: {e}", file=sys.stderr)
            continue
        for j in batch:
            r = scored.get(j.id)
            if r:
                used = True
                _apply(j, r, weights)
    print(f"  ai analyzed {sum(1 for j in jobs if j.ai_reason)} jobs", file=sys.stderr)
    return jobs, used
