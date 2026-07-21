"""Daily pipeline: fetch -> keyword pre-filter -> LLM semantic score -> email.

Multi-profile: each career direction lives in profiles/<name>/ with its own
profile.yaml (overrides base config.yaml) + resume.md, and gets its own email
and dedupe state.

Run:
  python -m src.main                      # run every profile
  python -m src.main --profile ai-risk    # one profile
  python -m src.main --dry-run            # print, no email, no state write
"""
from __future__ import annotations

import argparse
import copy
import sys
import time
from datetime import date
from pathlib import Path

import yaml

from . import ai_score, digest, notify_email, store
from .fetch import fetch_all
from .score import build_profile, score_all

ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = ROOT / "profiles"


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {**out[k], **v}
        else:
            out[k] = copy.deepcopy(v)
    return out


def discover_profiles() -> list[str]:
    if not PROFILES_DIR.exists():
        return []
    return sorted(p.name for p in PROFILES_DIR.iterdir() if (p / "profile.yaml").exists())


def load_context(profile: str | None) -> tuple[dict, str, str, str]:
    """Return (cfg, resume_text, namespace, label)."""
    base = yaml.safe_load((ROOT / "config.yaml").read_text()) or {}
    if profile:
        pdir = PROFILES_DIR / profile
        override = yaml.safe_load((pdir / "profile.yaml").read_text()) or {}
        cfg = _merge(base, override)
        resume = _read_resume(pdir)
        label = cfg.get("label", profile)
        return cfg, resume, profile, label
    # legacy single-profile fallback
    return base, _read_resume(ROOT / "profile"), "default", base.get("label", "findjob")


def _read_resume(dir_: Path) -> str:
    pdf = dir_ / "resume.pdf"
    if pdf.exists():
        try:
            from pypdf import PdfReader

            text = "\n".join((p.extract_text() or "") for p in PdfReader(str(pdf)).pages)
            if text.strip():
                return text
        except Exception as e:
            print(f"  could not read {pdf} ({e}); falling back", file=sys.stderr)
    for name in ("resume.md", "resume.txt"):
        p = dir_ / name
        if p.exists():
            return p.read_text()
    return ""


def collect_profile(profile: str | None, dry_run: bool = False) -> dict:
    """Fetch + score one profile. Writes dedupe/last-run state unless dry_run.
    Returns {cfg, label, ns, top, meta, tailored} — no email sent here."""
    cfg, resume, ns, label = load_context(profile)
    prof = build_profile(cfg, resume)
    acfg = cfg.get("ai_scoring", {}) or {}

    print(f"\n=== profile: {label} ===", file=sys.stderr)
    jobs = fetch_all(cfg)
    scanned = len(jobs)

    try:
        from . import dream
        flagged = dream.flag_dream(jobs)
        if flagged:
            print(f"  dream: flagged {flagged} aggregator jobs at Target-50 companies", file=sys.stderr)
    except Exception as e:
        print(f"  dream flagging skipped: {e}", file=sys.stderr)

    prefilter = acfg.get("prefilter_min_score", cfg.get("min_score", 25)) if acfg.get("enabled") else cfg.get("min_score", 25)
    candidates = score_all(jobs, prof, prefilter)

    seen = store.load_seen(ns)
    now = time.time()
    if cfg.get("new_only", True):
        candidates = [j for j in candidates if j.id not in seen]

    if acfg.get("enabled"):
        candidates = candidates[: acfg.get("max_candidates", 40)]
        candidates, used_ai, ai_note = ai_score.rescore(candidates, resume, cfg)
    else:
        used_ai, ai_note = False, ""

    min_score = cfg.get("min_score", 25)
    ranked = sorted(
        [j for j in candidates if j.rank_score >= min_score and j.ai_location_ok],
        key=lambda j: j.rank_score,
        reverse=True,
    )
    top = ranked[: cfg.get("top_n", 25)]
    for j in top:
        seen[j.id] = now

    tailored = _auto_tailor(top, resume, cfg)
    meta = {"scanned": scanned, "min_score": min_score, "used_ai": used_ai,
            "ai_note": ai_note, "label": label}

    if not dry_run:
        store.save_seen(seen, ns)
        store.save_last_run([j.to_dict() for j in top], ns)
    return {"cfg": cfg, "resume": resume, "label": label, "ns": ns,
            "top": top, "meta": meta, "tailored": tailored}


def run_profile(profile: str | None, dry_run: bool) -> int:
    """Legacy per-profile mode: collect then email this profile's own digest."""
    res = collect_profile(profile, dry_run)
    top, meta, tailored, label = res["top"], res["meta"], res["tailored"], res["label"]
    text_body = digest.build_text(top, meta, tailored)
    html_body = digest.build_html(top, meta, tailored)
    subject = f"[findjob · {label}] {date.today().isoformat()} · {len(top)} 个匹配岗位"

    print(text_body)
    if dry_run:
        print(f"\n(dry-run: {label} 未发邮件、未写入状态)", file=sys.stderr)
        return 0

    if top:
        notify_email.send(subject, text_body, html_body)
    else:
        print(f"  {label}: no jobs above threshold; skipping email", file=sys.stderr)
    return 0


def _auto_tailor(top, resume: str, cfg: dict) -> dict[str, str]:
    n = int(cfg.get("auto_tailor_top", 0) or 0)
    if n <= 0 or not top:
        return {}
    try:
        from .tailor import generate
    except Exception:
        return {}
    out: dict[str, str] = {}
    for j in top[:n]:
        try:
            out[j.id] = generate(resume, j.to_dict())
        except SystemExit as e:
            print(f"  auto-tailor skipped: {e}", file=sys.stderr)
            break
        except Exception as e:
            print(f"  auto-tailor failed for {j.title}: {e}", file=sys.stderr)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", help="只跑某个 profile（profiles/ 下的目录名）")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.profile:
        return run_profile(args.profile, args.dry_run)

    profiles = discover_profiles()
    if not profiles:
        return run_profile(None, args.dry_run)  # legacy single
    rc = 0
    for name in profiles:
        rc |= run_profile(name, args.dry_run)
    return rc


if __name__ == "__main__":
    sys.exit(main())
