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


# ---- 职级带（候选人 ~10 年经验 ≈ 行业 Senior Manager 段）--------------------
# 甜蜜区: senior manager / lead / principal / VP(银行语境) / director / associate director
# 直接丢弃: 真正的 C-suite / Partner / Global Head —— 高 1-2 级，投递纯浪费
#
# 注意: "Managing Director" 在银行里不能一刀切丢弃！大行(Citi/GS/MS/JPM/BofA)
# 把 MD 当成一个跨度很大的职级带（比如 Citi 内部 C15-C19 都叫 MD，C16 这种更接近
# SVP），不是 PE/企业语境里的真 C-suite。"Managing Director, Responsible AI Lead"
# 这类头衔挂 MD、内容是动手做治理框架的 working lead 岗，应该进候选池（降级展示），
# 而不是被误杀。所以 MD 放进"冲刺区"降分保留，交给 GPT 层按 JD 里的年限/职责范围
# 再精细判断；只有明确的 Chief * Officer / CEO-CFO-COO 等 / Partner / Global Head
# 才是真正高 1-2 级、直接丢弃。
TITLE_TOO_SENIOR = re.compile(
    r"\b(chief\s+[a-z]+\s+officer|ceo|cfo|coo|cro|ciso|cio"
    r"|partner|global head)\b", re.I)
# 冲刺区（高半级~一级）: 保留但降分——含银行语境的 Managing Director
TITLE_STRETCH = re.compile(
    r"\b(managing director|executive director|senior vice president|svp|evp|head of)\b", re.I)
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
        # opt-in seniority / experience gates (see _MANAGER_PLUS, extract_required_years):
        #   require_seniority -> title must be manager-level or above
        #   min_years         -> drop roles whose JD targets a clearly junior band
        #   min_skill_hits    -> require at least N of YOUR skills to appear in the JD
        #                        (i.e. a real chunk of the role's asks overlaps your profile)
        "require_seniority": bool(cfg.get("require_title_seniority", False)),
        "min_years": cfg.get("min_years"),
        "min_skill_hits": int(cfg.get("min_skill_hits", 0) or 0),
        # combo_boost = 交叉岗加分。每条规则给出若干组词，岗位必须**每组都命中
        # 至少一个**才算这个组合。用来抓"同时是 A 又是 B"的岗位——比如
        # AI × 审计：既要 AI/GenAI 又要 audit/SOX，正好卡在候选人的独特画像上。
        "combos": _build_combos(cfg.get("combo_boost") or []),
    }


def _build_combos(raw: list) -> list[dict]:
    out = []
    for rule in raw:
        groups = [[_norm(t) for t in g if str(t).strip()]
                  for g in (rule.get("all_of") or [])]
        groups = [g for g in groups if g]
        if len(groups) < 2:
            continue                      # 少于两组就不叫"组合"了
        out.append({
            "label": rule.get("label") or "combo",
            "groups": groups,
            "points": float(rule.get("points", 15)),
            "title_points": float(rule.get("title_points", 0)),
            # 每组在正文里至少要命中几个**不同**的词才算数。现在几乎每份 JD
            # 都会顺嘴提一句 AI，只要 1 个词就算命中的话，一半的审计岗都会
            # 被误判成"AI 交叉岗"。
            "min_body": int(rule.get("min_body_hits", 2)),
            # 哪几组**必须**出现在标题里（组的下标，从 0 开始）。
            # 关键在于：要求"稀有的那一边"进标题。在内部审计的 feed 里，
            # audit 满地都是、AI 才是区分点，所以要求 AI 进标题；在 AI 治理的
            # feed 里反过来。不指定就退回"至少任意一组进标题"。
            "title_groups": [int(i) for i in (rule.get("title_groups") or [])],
            "require_title": bool(rule.get("require_title", True)),
        })
    return out


def apply_combos(job: Job, prof: dict, blob: str, title: str) -> float:
    """命中的组合给加分，并在 job.combo 上打标记（邮件里据此置顶 + 标注）。

    一组算"命中"有两条路：出现在标题里，或者在正文里出现 ≥min_body 个不同的词。
    再要求至少一组落在标题上，才算真的是为这个交叉画像开的岗——
    否则只是一个审计岗在 JD 里提了两句 AI。
    """
    bonus = 0.0
    hits: list[str] = []
    for c in prof.get("combos") or []:
        in_title, ok, evidence = [], True, []
        for g in c["groups"]:
            t_hits = [t for t in g if _present(t, title)]
            b_hits = [t for t in g if _present(t, blob)]
            in_title.append(bool(t_hits))
            if not (t_hits or len(b_hits) >= c["min_body"]):
                ok = False
                break
            evidence += (t_hits or b_hits)[:2]
        if not ok:
            continue
        need = c["title_groups"]
        if need:
            if not all(in_title[i] for i in need if i < len(in_title)):
                continue
        elif c["require_title"] and not any(in_title):
            continue
        bonus += c["points"]
        if all(in_title):                    # 标题里就写明了两边——最强信号
            bonus += c["title_points"]
        hits.append(c["label"])
        job.matched = list(dict.fromkeys(job.matched + evidence))
    if hits:
        job.combo = " / ".join(hits)
    return bonus


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
# title words that signal manager-level or above. Used by the opt-in seniority
# gate (require_title_seniority) so a direction can demand "at least manager"
# and drop individual-contributor roles ("Internal Auditor", "Senior Auditor").
# NOTE: "senior" is deliberately NOT here — a Senior Auditor is still an IC.
_MANAGER_PLUS = {
    "manager", "director", "head", "vp", "vice", "president",
    "principal", "lead", "chief", "officer", "partner", "cae",
}

# Pull the minimum years-of-experience a JD asks for, so a direction can drop
# roles clearly aimed at a more junior band than the candidate. Matches
# "5+ years", "5-7 years", "minimum of 8 years", "6 years of experience".
# Returns the LOWEST stated bar (the entry requirement), or None if unstated.
_YEARS_PATS = [
    re.compile(r"(\d{1,2})\s*\+?\s*(?:to|-|–|—)\s*\d{1,2}\s*\+?\s*years", re.I),
    re.compile(r"(\d{1,2})\s*\+\s*years", re.I),
    re.compile(r"(?:minimum|at least|min\.?|minimum of|a minimum of)\s*(\d{1,2})\s*years", re.I),
    re.compile(r"(\d{1,2})\s*years?\s+(?:of\s+)?(?:relevant\s+|related\s+|progressive\s+)?(?:work\s+)?experience", re.I),
]


def extract_required_years(text: str) -> int | None:
    yrs: list[int] = []
    for pat in _YEARS_PATS:
        for m in pat.finditer(text):
            n = int(m.group(1))
            if 1 <= n <= 30:
                yrs.append(n)
    return min(yrs) if yrs else None


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
    title_norm = _norm(job.title)
    if TITLE_TOO_SENIOR.search(title_norm):   # MD/C-level/Partner：不抓
        job.score = 0.0
        return job
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

    # ---- seniority / experience gates (opt-in per direction) ----
    # Fire only when the profile sets the keys, so focus directions (e.g. AI
    # governance) are untouched unless they opt in. This is what enforces
    # "at least manager, ~6-8+ years" for internal audit.
    min_years = prof.get("min_years")
    req_years = extract_required_years(blob) if min_years else None
    if prof.get("require_seniority"):
        tw = set(re.findall(r"[a-z]+", title))
        if not (tw & _MANAGER_PLUS):
            job.score = 0.0          # individual-contributor / unspecified level
            return job
    if min_years and req_years is not None and req_years < min_years - 2:
        job.score = 0.0              # JD explicitly aims at a junior band
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
    # require a real overlap between the JD and your profile: at least N of your
    # skills must show up in the posting, else it's only a loose title match.
    if prof.get("min_skill_hits") and len(matched) < prof["min_skill_hits"]:
        job.score = 0.0
        return job
    skill_ratio = len(matched) / max(len(prof["skills"]), 1)
    skill_score = min(len(matched_core) * 14 + len(matched_other) * 5, 60) + skill_ratio * 10

    # nice-to-have + location bonuses
    bonus = sum(4 for n in prof["nice_to_have"] if _present(n, blob))
    if not prof["remote_only"] and prof["locations"]:
        if any(_present(l, blob) for l in prof["locations"]):
            bonus += 6
    bonus += recency_bonus(job.posted)

    # seniority + experience-band rewards (only for directions that opt in)
    if prof.get("require_seniority") or min_years:
        tw = set(re.findall(r"[a-z]+", title))
        if tw & _MANAGER_PLUS:
            bonus += 8
        elif tw & _JUNIOR_WORDS:
            bonus -= 15
        if min_years and req_years is not None and min_years <= req_years <= min_years + 9:
            bonus += 6               # JD's stated band matches your 6-8+ yrs

    # 职级带调整：冲刺岗降分保留，低于段位重降分（与上面的 opt-in 门槛互补，
    # 对所有方向生效——按标题正则识别"够一段"与"低于段位"的岗位）
    band_penalty = 0
    if TITLE_STRETCH.search(title_norm):
        band_penalty = STRETCH_PENALTY
    elif TITLE_TOO_JUNIOR.search(title_norm):
        band_penalty = JUNIOR_PENALTY

    bonus += apply_combos(job, prof, blob, title)

    job.score = round(min(max(skill_score + title_score + bonus - band_penalty, 0), 100), 1)

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
    score += apply_combos(job, prof, blob, title)
    job.score = round(min(max(score, 0), 100), 1)
    return job


def score_all(jobs: list[Job], prof: dict, min_score: float) -> list[Job]:
    scored = [score_job(j, prof) for j in jobs]
    kept = [j for j in scored if j.score >= min_score]
    kept.sort(key=lambda j: j.score, reverse=True)
    return kept
