"""Story Library loader — career/stories/*.md as reusable STAR material.

Each story file has a light front matter:
    ---
    title: ...
    tags: [a, b, c]
    use_for: [resume, cover-letter, interview]
    ---
    body...

`select(jd_text, k)` ranks stories by tag/keyword overlap with a JD so
tailor.py and interview.py can inject only the most relevant ones.

CLI:  python -m src.stories                 # list stories
      python -m src.stories --jd "paste JD" # show best matches for a JD
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORIES_DIR = ROOT / "career" / "stories"

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class Story:
    path: str
    title: str
    tags: list[str] = field(default_factory=list)
    use_for: list[str] = field(default_factory=list)
    body: str = ""


def _parse_list(val: str) -> list[str]:
    val = val.strip()
    if val.startswith("[") and val.endswith("]"):
        return [x.strip().strip("'\"") for x in val[1:-1].split(",") if x.strip()]
    return [val] if val else []


def load() -> list[Story]:
    if not STORIES_DIR.exists():
        return []
    out = []
    for p in sorted(STORIES_DIR.glob("*.md")):
        if p.name.startswith(("_", "README")):
            continue
        text = p.read_text()
        m = _FM_RE.match(text)
        title, tags, use_for, body = p.stem, [], [], text
        if m:
            body = text[m.end():]
            for line in m.group(1).splitlines():
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k = k.strip().lower()
                if k == "title":
                    title = v.strip()
                elif k == "tags":
                    tags = [t.lower() for t in _parse_list(v)]
                elif k == "use_for":
                    use_for = _parse_list(v)
        out.append(Story(path=p.name, title=title, tags=tags, use_for=use_for, body=body.strip()))
    return out


def select(jd_text: str, k: int = 3, purpose: str | None = None) -> list[Story]:
    """Best-matching stories for a JD by tag hits (title words as tiebreaker)."""
    jd = (jd_text or "").lower()
    scored = []
    for s in load():
        if purpose and s.use_for and purpose not in s.use_for:
            continue
        hits = sum(1 for t in s.tags if t in jd)
        hits += 0.2 * sum(1 for w in re.findall(r"[a-z]{4,}", s.title.lower()) if w in jd)
        scored.append((hits, s))
    scored.sort(key=lambda x: -x[0])
    return [s for h, s in scored[:k] if h > 0] or [s for _, s in scored[:k]]


def as_prompt_block(stories: list[Story], max_chars: int = 4500) -> str:
    """Stories rendered for prompt injection (grounding material)."""
    parts = []
    for s in stories:
        parts.append(f"### {s.title}\n{s.body}")
    return "\n\n".join(parts)[:max_chars]


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--jd", help="粘贴 JD，输出最匹配的故事")
    args = ap.parse_args()
    if args.jd:
        for s in select(args.jd, 3):
            print(f"★ {s.title}  [{', '.join(s.tags[:5])}]")
        return
    stories = load()
    if not stories:
        print("career/stories/ 下还没有故事文件", file=sys.stderr)
    for s in stories:
        print(f"- {s.title}  ({s.path})")


if __name__ == "__main__":
    main()
