"""Content-based matching: score a job against YOUR profile, not its title.

The score answers "does this job's actual described work overlap with what I do
and want?" — skills/keywords carry the most weight; title is a light signal.
It also surfaces `matched` (why it fits) and `missing` (gap keywords the JD asks
for that your profile doesn't show yet) so you can decide, truthfully, whether
to highlight something you already have.
"""
from __future__ import annotations

import re

from .sources.base import Job


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


# ---- 职级带（候选人 ~10 年经验 ≈ 行业 Senior Manager 段）--------------------
# 甜蜜区: senior manager / lead / principal / VP(银行语境) / director / associate director
# 直接丢弃: MD / C-level / Partner / Global Head —— 高 1-2 级，投递纯浪费
TITLE_TOO_SENIOR = re.compile(
    r"\b(managing director|chief\s+[a-z]+\s+officer|ceo|cfo|coo|cro|ciso|cio"
    r"|partner|global head)\b", re.I)
# 冲刺区（高半级~一级）: 保留但降分
TITLE_STRETCH = re.compile(
    r"\b(executive director|senior vice president|svp|evp|head of)\b", re.I)
# 低于段位: 重降分（注意 associate director 属于甜蜜区，不算 junior）
TITLE_TOO_JUNIOR = re.compile(
    r"\b(junior|coordinator|analyst|associate(?!\s*director))\b", re.I)
STRETCH_PENALTY = 12
JUNIOR_PENALTY = 18


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
        "locations": [_norm(t) for t in cfg.get("locations", [])],
        "remote_only": bool(cfg.get("remote_only", False)),
    }


def score_job(job: Job, prof: dict) -> Job:
    blob = job.blob

    # hard filters -> score 0 means "drop"
    title_norm = _norm(job.title)
    if TITLE_TOO_SENIOR.search(title_norm):   # MD/C-level/Partner：不抓
        job.score = 0.0
        return job
    for bad in prof["exclude"]:
        if _present(bad, blob):
            job.score = 0.0
            return job
    for req in prof["must_have"]:
        if not _present(req, blob):
            job.score = 0.0
            return job
    if prof["remote_only"] and not (job.remote or _present("remote", blob)):
        job.score = 0.0
        return job

    # skill overlap — the main signal
    matched = [s for s in prof["skills"] if _present(s, blob)]
    job.matched = matched
    skill_ratio = len(matched) / max(len(prof["skills"]), 1)
    skill_score = min(len(matched) * 9, 60) + skill_ratio * 10  # up to ~70

    # title relevance — light signal
    title = _norm(job.title)
    title_score = 0
    for t in prof["titles"]:
        if t and t in title:
            title_score = 20
            break
        # partial: any significant word of a target title in the job title
        words = [w for w in t.split() if len(w) > 3]
        if words and sum(w in title for w in words) >= max(1, len(words) - 1):
            title_score = max(title_score, 12)

    # nice-to-have + location bonuses
    bonus = sum(4 for n in prof["nice_to_have"] if _present(n, blob))
    if not prof["remote_only"] and prof["locations"]:
        if any(_present(l, blob) for l in prof["locations"]):
            bonus += 6

    # 职级带调整：冲刺岗降分保留，低于段位重降分
    band_penalty = 0
    if TITLE_STRETCH.search(title_norm):
        band_penalty = STRETCH_PENALTY
    elif TITLE_TOO_JUNIOR.search(title_norm):
        band_penalty = JUNIOR_PENALTY

    job.score = round(min(max(skill_score + title_score + bonus - band_penalty, 0), 100), 1)

    # gap keywords: skills the JD clearly asks for that aren't yours yet
    missing = [s for s in prof["skills"] if s not in matched and _present(s, blob)]
    job.missing = missing
    return job


def score_all(jobs: list[Job], prof: dict, min_score: float) -> list[Job]:
    scored = [score_job(j, prof) for j in jobs]
    kept = [j for j in scored if j.score >= min_score]
    kept.sort(key=lambda j: j.score, reverse=True)
    return kept
