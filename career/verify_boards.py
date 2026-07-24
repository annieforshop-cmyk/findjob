"""Probe the candidate pool and promote the LIVE boards into ats_companies.yaml.

The daily run (src/sources/ats_boards.py) reads only ats_companies.yaml — the
*verified* list — so it stays fast and clean. This script probes every board in
ats_candidates.yaml (+ the current verified list), keeps the ones that actually
return jobs, and rewrites ats_companies.yaml. Wrong token guesses in the big
candidate pool simply fail here and never reach the daily run.

Runs where the network is open (GitHub Actions). Locally it needs outbound
access to the ATS hosts.

  python career/verify_boards.py                 # probe all, rewrite ats_companies.yaml
  python career/verify_boards.py --dry-run       # probe, print, write nothing
  python career/verify_boards.py --limit 50      # probe first 50 (quick test)
  python career/verify_boards.py --workers 32    # more concurrency
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
from src.sources.ats_boards import _FETCHERS  # noqa: E402

CANDIDATES = ROOT / "ats_candidates.yaml"
LIVE = ROOT / "ats_companies.yaml"
KIND_ORDER = ["workday", "greenhouse", "lever", "ashby", "smartrecruiters"]


def _load(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return (yaml.safe_load(p.read_text()) or {}).get("companies", [])


def _key(c: dict) -> tuple:
    return (c.get("kind"), c.get("token") or c.get("host"))


def _probe(c: dict) -> tuple[dict, int, str]:
    try:
        jobs = _FETCHERS[c["kind"]](c)
        return c, len(jobs), ""
    except Exception as e:  # noqa: BLE001 — record and move on
        return c, 0, str(e)[:90]


def _clean(c: dict, verified: str) -> dict:
    """Emit a tidy row: name, kind, token/host/site, verified."""
    out = {"name": c.get("name", "?"), "kind": c["kind"]}
    for f in ("token", "host", "site"):
        if c.get(f):
            out[f] = c[f]
    out["verified"] = verified
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="probe but don't write")
    ap.add_argument("--limit", type=int, default=0, help="probe only first N (test)")
    ap.add_argument("--workers", type=int, default=24)
    args = ap.parse_args()

    live = _load(LIVE)
    live_keys = {_key(c) for c in live}
    live_verified = {_key(c): c.get("verified") for c in live if c.get("verified")}

    merged: dict[tuple, dict] = {}
    for c in live + _load(CANDIDATES):            # existing verified first
        if c.get("kind") in _FETCHERS and _key(c)[1]:
            merged.setdefault(_key(c), c)
    items = list(merged.values())
    if args.limit:
        items = items[: args.limit]

    print(f"probing {len(items)} boards with {args.workers} workers…", file=sys.stderr)
    today = dt.date.today().isoformat()
    survivors: list[tuple[int, dict]] = []
    live_kept = 0
    new_promoted = 0
    dead = 0

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(_probe, c): c for c in items}
        for fut in as_completed(futs):
            c, n, err = fut.result()
            k = _key(c)
            if n > 0:
                survivors.append((n, _clean(c, today)))
                if k not in live_keys:
                    new_promoted += 1
            elif k in live_verified:
                # was verified before — keep on a transient miss, don't nuke it
                survivors.append((0, _clean(c, live_verified[k])))
                live_kept += 1
            else:
                dead += 1

    # order: by kind, then by job count desc
    survivors.sort(key=lambda t: (KIND_ORDER.index(t[1]["kind"])
                                  if t[1]["kind"] in KIND_ORDER else 99, -t[0]))
    rows = [r for _, r in survivors]

    live_now = sum(1 for n, _ in survivors if n > 0)
    print(f"  live now: {live_now} | kept (transient miss): {live_kept} | "
          f"newly promoted: {new_promoted} | dropped: {dead} | total kept: {len(rows)}",
          file=sys.stderr)

    if args.dry_run:
        print("(dry-run: ats_companies.yaml not written)", file=sys.stderr)
        return 0

    header = (
        "# ============================================================\n"
        "#  ATS 直连清单 — 由 career/verify_boards.py 自动维护（每周 CI 刷新）。\n"
        "#  只包含最近一次验证真的抓到过岗位的公司；候选池在 ats_candidates.yaml。\n"
        f"#  最近验证：{today}。手动加公司请加到 gen_candidates.py 再跑验证。\n"
        "# ============================================================\n"
    )
    body = yaml.safe_dump({"companies": rows}, sort_keys=False, allow_unicode=True,
                          width=200, default_flow_style=False)
    LIVE.write_text(header + body)
    print(f"wrote {LIVE} — {len(rows)} verified companies", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
