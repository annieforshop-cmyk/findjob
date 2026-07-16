"""Daily pipeline: fetch -> keyword pre-filter -> LLM semantic score -> email.

Run locally:   python -m src.main            (sends email if SMTP env set)
               python -m src.main --dry-run  (prints digest, no email, no state write)
"""
from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path

import yaml

from . import ai_score, digest, notify_email, store
from .fetch import fetch_all
from .score import build_profile, score_all

ROOT = Path(__file__).resolve().parent.parent


def load_cfg() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def load_resume() -> str:
    """Resume from PDF (preferred if present), else Markdown, else text."""
    prof_dir = ROOT / "profile"
    pdf = prof_dir / "resume.pdf"
    if pdf.exists():
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
            if text.strip():
                return text
            print("  resume.pdf had no extractable text; falling back", file=sys.stderr)
        except Exception as e:
            print(f"  could not read resume.pdf ({e}); falling back", file=sys.stderr)
    for name in ("resume.md", "resume.txt"):
        p = prof_dir / name
        if p.exists():
            return p.read_text()
    return ""


def run(dry_run: bool = False) -> int:
    cfg = load_cfg()
    resume = load_resume()
    prof = build_profile(cfg, resume)
    acfg = cfg.get("ai_scoring", {}) or {}

    print("fetching sources...", file=sys.stderr)
    jobs = fetch_all(cfg)
    scanned = len(jobs)

    # stage 1: cheap keyword net (wide when AI scoring will refine it)
    prefilter = acfg.get("prefilter_min_score", cfg.get("min_score", 25)) if acfg.get("enabled") else cfg.get("min_score", 25)
    candidates = score_all(jobs, prof, prefilter)

    # cross-day dedupe before spending LLM tokens
    seen = store.load_seen()
    now = time.time()
    if cfg.get("new_only", True):
        candidates = [j for j in candidates if j.id not in seen]

    # stage 2: LLM semantic scoring on a capped candidate set
    if acfg.get("enabled"):
        candidates = candidates[: acfg.get("max_candidates", 40)]
        candidates, used_ai = ai_score.rescore(candidates, resume, cfg)
    else:
        used_ai = False

    # final ranking uses AI fit when available, else keyword score
    min_score = cfg.get("min_score", 25)
    ranked = sorted(
        [j for j in candidates if j.rank_score >= min_score],
        key=lambda j: j.rank_score,
        reverse=True,
    )
    top = ranked[: cfg.get("top_n", 25)]

    for j in top:
        seen[j.id] = now

    # optional: pre-write cover-letter drafts for the very best matches
    tailored = _auto_tailor(top, resume, cfg)

    meta = {"scanned": scanned, "min_score": min_score, "used_ai": used_ai}
    text_body = digest.build_text(top, meta, tailored)
    html_body = digest.build_html(top, meta, tailored)
    subject = f"[findjob] {date.today().isoformat()} · {len(top)} 个匹配岗位"

    print(text_body)

    if dry_run:
        print("\n(dry-run: 未发邮件、未写入状态)", file=sys.stderr)
        return 0

    if top:
        notify_email.send(subject, text_body, html_body)
    else:
        print("  no jobs above threshold; skipping email", file=sys.stderr)

    store.save_seen(seen)
    store.save_last_run([j.to_dict() for j in top])
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
        except SystemExit as e:  # tailor uses sys.exit on missing key
            print(f"  auto-tailor skipped: {e}", file=sys.stderr)
            break
        except Exception as e:
            print(f"  auto-tailor failed for {j.title}: {e}", file=sys.stderr)
    return out


if __name__ == "__main__":
    sys.exit(run(dry_run="--dry-run" in sys.argv))
