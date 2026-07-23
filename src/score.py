"""Content-based matching: score a job against YOUR profile, not its title.

The score answers "does this job's actual described work overlap with what I do
and want?" — skills/keywords carry the most weight; title is a light signal.
It also surfaces `matched` (why it fits) and `missing` (gap keywords the JD asks
for that your profile doesn't show yet) so you can decide, truthfully, whether
to highlight something you already have.
"""
from __future__ import annotations

import datetime as dt
import re

from .sources.base import Job


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def _present(term: str, text: str) -> bool:
    """Whole-word-ish containment so 'r' doesn't match 'react'."""
    t = _norm(term)
    if not t:
        return False
    if not re.search(r"[a-z0-9]", t[0]) or not re.search(r"[a-z0-9]", t[-1]):
        return t in text  # symbols like c++ / a/b — fall back to substring
    return re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", text) is not None


def build_profile(cfg: dict, resume_text: str) -> dict:
    resume = _norm(resume_text)
    skills = [_norm(s) for s in cfg.get("skills", []) if s.strip()]
    # a skill counts as "yours" if it's in config skills OR literally in your resume
    owned = set(skills)
    return {
        "skills": skills,
        "owned": owned,
        "resume": resume,
        "titles": [_norm(t) for t in cfg.get("target_titles", [])],
        "must_have": [_norm(t) for t in cfg.get("must_have", [])],
        "nice_to_have": [_norm(t) for t in cfg.get("nice_to_have", [])],
        "exclude": [_norm(t) for t in cfg.get("exclude_keywords", [])],
        # core skills = words that actually SIGNAL this role family (e.g. "internal
        # audit", "model risk"), as opposed to generic resume words ("banking",
        # "cpa") that appear in every fintech JD. A job must hit at least one core
        # skill or a target title, or it is dropped — this is what keeps
        # "Customer Success Manager" out of an audit brief.
        "core": [_norm(t) for t in cfg.get("core_skills", [])],
        # title-level exclusions: role families never worth showing, matched
        # against the TITLE only (JD text mentions "sales" too often to use blob)
        "exclude_title": [_norm(t) for t in cfg.get("exclude_title_keywords", [])],
        # focus_terms = the ONE central theme the role must be about (e.g. AI
        # governance). Precision gate: the job must have a focus term in its
        # TITLE, or >=2 distinct focus terms in its body — otherwise it's a
        # role that merely mentions the theme in boilerplate and is dropped.
        # When set, scoring is driven by focus + business_signals (no LLM needed).
        "focus": [_norm(t) for t in cfg.get("focus_terms", [])],
        # business_signals = evidence the role wants a business/governance/risk
        # background driving the theme, not a hands-on ML builder.
        "business": [_norm(t) for t in cfg.get("business_signals", [])],
        "locations": [_norm(t) for t in cfg.get("locations", [])],
        "remote_only": bool(cfg.get("remote_only", False)),
        "us_only": bool(cfg.get("us_only", True)),
    }


# title words that signal an appropriate senior/business level for these roles
_SENIOR_WORDS = {
    "director", "head", "lead", "leader", "manager", "senior", "principal",
    "vp", "vice", "chief", "officer", "governance", "counsel", "president",
}
# title words that signal a hands-on / junior role this candidate doesn't want
_JUNIOR_WORDS = {
    "intern", "internship", "coordinator", "assistant", "entry", "junior",
    "engineer", "developer", "scientist", "researcher",
}


# location strings that clearly place a job OUTSIDE the US. Word-boundary
# matched; a posting that ALSO names a US location is kept (multi-location).
_NON_US = [
    "united kingdom", "uk", "london", "ireland", "dublin", "canada", "toronto",
    "vancouver", "ottawa", "montreal", "india", "bengaluru", "bangalore",
    "mumbai", "hyderabad", "pune", "singapore", "australia", "sydney",
    "melbourne", "france", "paris", "germany", "berlin", "munich",
    "netherlands", "amsterdam", "spain", "madrid", "poland", "warsaw",
    "brazil", "sao paulo", "mexico", "japan", "tokyo", "seoul", "korea",
    "china", "hong kong", "taiwan", "cyprus", "israel", "tel aviv", "dubai",
    "uae", "switzerland", "zurich", "geneva", "sweden", "stockholm",
    "denmark", "copenhagen", "portugal", "lisbon", "italy", "milan",
    "belgium", "brussels", "austria", "vienna", "philippines", "manila",
    "colombia", "argentina", "chile", "new zealand", "egypt", "nigeria",
    "south africa", "malaysia", "indonesia", "thailand", "vietnam",
    "europe", "emea", "apac", "latam", "quezon", "cebu", "gurgaon",
    "gurugram", "noida", "chennai", "kolkata", "krakow", "wroclaw",
    "bucharest", "sofia", "istanbul", "riyadh", "doha", "nairobi",
]
_US_MARKERS = [
    "united states", "usa", "u.s.", "america", "us-based", "remote us",
    "us remote", "remote - us", "remote, us", "new york", "san francisco",
    "chicago", "boston", "austin", "seattle", "denver", "atlanta", "dallas",
    "charlotte", "miami", "washington", "los angeles", "houston", "phoenix",
    "philadelphia", "columbus", "nashville", "jacksonville", "salt lake",
]
_US_STATE_ABBR = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}


def location_is_non_us(location: str) -> bool:
    """True only when the location names a non-US place and NO US place.
    Empty/unknown locations return False (kept — the LLM pass judges those)."""
    loc = _norm(location)
    if not loc:
        return False
    if not any(_present(m, loc) for m in _NON_US):
        return False
    if any(_present(m, loc) for m in _US_MARKERS):
        return False
    if _US_STATE_ABBR & set(re.findall(r"\b[A-Z]{2}\b", location)):
        return False
    return True


def recency_bonus(posted: str) -> float:
    """ApplyPilot-style freshness: fresh postings convert better, stale ones
    are likely filled or ghost. Unknown dates are neutral."""
    try:
        age = (dt.date.today() - dt.date.fromisoformat(posted[:10])).days
    except (ValueError, TypeError):
        return 0.0
    if age <= 2:
        return 8.0
    if age <= 7:
        return 4.0
    if age <= 21:
        return 0.0
    return -6.0


# words too generic to establish title relevance on their own
_GENERIC_TITLE_WORDS = {
    "senior", "manager", "director", "head", "lead", "vice", "president",
    "principal", "staff", "associate", "analyst", "chief", "officer",
    "global", "executive",
}


def score_job(job: Job, prof: dict) -> Job:
    blob = job.blob
    title = _norm(job.title)

    # hard filters -> score 0 means "drop"
    for bad in prof["exclude"]:
        if _present(bad, blob):
            job.score = 0.0
            return job
    for bad in prof.get("exclude_title", []):
        if _present(bad, title):
            job.score = 0.0
            return job
    for req in prof["must_have"]:
        if not _present(req, blob):
            job.score = 0.0
            return job
    if prof["remote_only"] and not (job.remote or _present("remote", blob)):
        job.score = 0.0
        return job
    if prof.get("us_only") and location_is_non_us(job.location):
        job.score = 0.0
        return job

    # ---- focus-driven precision path (no LLM needed) ----
    # When the profile declares focus_terms, the role must be CENTRALLY about
    # that theme, and we score it on theme centrality + business-background
    # signals + seniority + freshness. This is what makes AI-governance matching
    # accurate without any OpenAI call.
    focus = prof.get("focus") or []
    if focus:
        return _score_focus(job, prof, blob, title, focus)

    # title relevance — light signal
    title_score = 0
    title_hit = False
    for t in prof["titles"]:
        if t and t in title:
            title_score, title_hit = 20, True
            break
        # partial: significant words of a target title in the job title.
        # Seniority words ("senior", "manager", …) are excluded — matching on
        # those alone made "Senior Manager, Compensation" count as a title hit.
        words = [w for w in t.split() if len(w) > 3 and w not in _GENERIC_TITLE_WORDS]
        if words and sum(w in title for w in words) >= max(1, len(words) - 1):
            title_score, title_hit = max(title_score, 12), True

    # skill overlap — the main signal. Core skills (role-defining terms) weigh
    # far more than generic resume words, and a job matching NO core skill and
    # no target title is dropped outright.
    core = prof.get("core") or []
    matched_core = [s for s in core if _present(s, blob)]
    if core and not matched_core and not title_hit:
        job.score = 0.0
        return job
    matched_other = [s for s in prof["skills"] if s not in set(core) and _present(s, blob)]
    matched = matched_core + matched_other
    job.matched = matched
    skill_ratio = len(matched) / max(len(prof["skills"]), 1)
    skill_score = min(len(matched_core) * 14 + len(matched_other) * 5, 60) + skill_ratio * 10

    # nice-to-have + location bonuses
    bonus = sum(4 for n in prof["nice_to_have"] if _present(n, blob))
    if not prof["remote_only"] and prof["locations"]:
        if any(_present(l, blob) for l in prof["locations"]):
            bonus += 6
    bonus += recency_bonus(job.posted)

    job.score = round(min(max(skill_score + title_score + bonus, 0), 100), 1)

    # gap keywords: skills the JD clearly asks for that aren't yours yet
    missing = [s for s in prof["skills"] if s not in matched and _present(s, blob)]
    job.missing = missing
    return job


def _score_focus(job: Job, prof: dict, blob: str, title: str, focus: list[str]) -> Job:
    """Score a role that must be centrally about the profile's focus theme
    (e.g. AI governance). No LLM. Precision comes from three gates + weighting:
      1. Centrality: focus term in title, OR >=2 distinct focus terms in body.
      2. Business fit: rewards governance/risk/policy framing (the "business
         background driving responsible AI" the candidate has), not ML building.
      3. Seniority: rewards director/manager/lead/head; penalizes junior/hands-on.
    """
    focus_in_title = [t for t in focus if t in title]
    focus_in_body = [t for t in focus if _present(t, blob)]
    # centrality gate
    if not focus_in_title and len(focus_in_body) < 2:
        job.score = 0.0
        job.matched = []
        return job

    business = prof.get("business") or []
    biz_hits = [b for b in business if _present(b, blob)]

    # base by how central the theme is
    score = 45.0 if focus_in_title else 28.0
    # more distinct focus terms in the JD => more genuinely about the theme
    score += min(len(focus_in_body), 5) * 6          # up to +30
    # business/governance framing => wants this candidate's background
    score += min(len(biz_hits), 6) * 4               # up to +24

    # seniority read from the title
    words = set(re.findall(r"[a-z]+", title))
    if words & _SENIOR_WORDS:
        score += 8
    if words & _JUNIOR_WORDS:
        score -= 18

    score += recency_bonus(job.posted)
    if prof["locations"] and any(_present(l, blob) for l in prof["locations"]):
        score += 4

    job.matched = (focus_in_title + [t for t in focus_in_body if t not in focus_in_title]
                   + biz_hits)[:10]
    job.missing = [t for t in focus if t not in focus_in_body][:6]
    job.score = round(min(max(score, 0), 100), 1)
    return job


def score_all(jobs: list[Job], prof: dict, min_score: float) -> list[Job]:
    scored = [score_job(j, prof) for j in jobs]
    kept = [j for j in scored if j.score >= min_score]
    kept.sort(key=lambda j: j.score, reverse=True)
    return kept
