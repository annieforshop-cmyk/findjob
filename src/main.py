"""Daily pipeline: fetch -> score -> (new-only) -> email digest -> persist.

Run locally:   python -m src.main            (sends email if SMTP env set)
               python -m src.main --dry-run  (prints digest, no email, no state write)
"""
from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path

import yaml

from . import digest, notify_email, store
from .fetch import fetch_all
from .score import build_profile, score_all

ROOT = Path(__file__).resolve().parent.parent


def load_cfg() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text())


def load_resume() -> str:
    p = ROOT / "profile" / "resume.md"
    return p.read_text() if p.exists() else ""


def run(dry_run: bool = False) -> int:
    cfg = load_cfg()
    resume = load_resume()
    prof = build_profile(cfg, resume)

    print("fetching sources...", file=sys.stderr)
    jobs = fetch_all(cfg)
    scanned = len(jobs)

    scored = score_all(jobs, prof, cfg.get("min_score", 25))

    # cross-day dedupe
    seen = store.load_seen()
    now = time.time()
    if cfg.get("new_only", True):
        fresh = [j for j in scored if j.id not in seen]
    else:
        fresh = scored
    for j in scored:
        seen[j.id] = now

    top = fresh[: cfg.get("top_n", 25)]
    meta = {"scanned": scanned, "min_score": cfg.get("min_score", 25)}

    text_body = digest.build_text(top, meta)
    html_body = digest.build_html(top, meta)
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


if __name__ == "__main__":
    sys.exit(run(dry_run="--dry-run" in sys.argv))
