"""个人主页生成器 —— 让 LinkedIn 之外的搜索也能找到你。

专业岗位里 34% 的成功招聘来自 LinkedIn 以外的渠道；hireEZ / SeekOut 这类
AI sourcing 工具爬 45+ 平台和公开网页，ChatGPT / Perplexity 这类 AI 搜索
也在直接引用网页内容。一个带 **schema.org JSON-LD** 结构化标记的静态页，
是让这些系统"读懂你是谁"最省力的一步——它们不用猜，字段是明写的。

生成的是一个零依赖、单文件的 `site/index.html`，直接开 GitHub Pages 就能上线。

用法：
    cp persona.example.yaml persona.yaml   # 填好（persona.yaml 不进 git）
    python -m src.site --profile ai-governance

技能列表留空时，自动从最新的 `reports/*-inbound-<方向>.md` 里取——
也就是从你自己抓的真实 JD 里统计出来的高价值词。
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

import yaml

from .main import ROOT

PERSONA = ROOT / "persona.yaml"
SITE = ROOT / "site"
REPORTS = ROOT / "reports"


def skills_from_report(profile: str, limit: int = 30) -> list[str]:
    """从最新的 inbound 报告第 4 节（Skills 排序建议）里取技能。"""
    cands = sorted(REPORTS.glob(f"*-inbound-{profile}.md"))
    if not cands:
        return []
    text = cands[-1].read_text()
    sec = re.search(r"## 4\..*?\n(.*?)(?=\n## )", text, re.S)
    if not sec:
        return []
    out = []
    for line in sec.group(1).splitlines():
        m = re.match(r"\s*\d+\.\s+(.+?)(?:\s+←.*)?$", line)
        if m:
            out.append(m.group(1).strip())
    return out[:limit]


def json_ld(p: dict, skills: list[str]) -> str:
    """schema.org Person —— 机器读的那一份。

    jobTitle / knowsAbout / worksFor 是 AI sourcing 工具归类候选人的主要字段，
    所以这几个一定要填对，别只靠正文里的自然语言。
    """
    same_as = [u for u in (p.get("links") or {}).values() if u]
    data: dict = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": p.get("name", ""),
        "description": (p.get("about") or "").strip(),
        "jobTitle": p.get("job_title") or p.get("headline", ""),
        "knowsAbout": skills,
    }
    if p.get("location"):
        data["address"] = {"@type": "PostalAddress",
                           "addressLocality": p["location"]}
    if p.get("email"):
        data["email"] = f"mailto:{p['email']}"
    if p.get("company"):
        data["worksFor"] = {"@type": "Organization", "name": p["company"]}
    if same_as:
        data["sameAs"] = same_as
    if p.get("credentials"):
        data["hasCredential"] = [
            {"@type": "EducationalOccupationalCredential", "name": c}
            for c in p["credentials"]]
    if p.get("seeking"):
        data["seeks"] = {"@type": "Demand", "description": p["seeking"]}
    return json.dumps(data, ensure_ascii=False, indent=2)


CSS = """
:root{--fg:#111;--muted:#555;--line:#e3e3e3;--accent:#1a4d8f;--chip:#f2f5f9}
@media(prefers-color-scheme:dark){:root{--fg:#e8e8e8;--muted:#a0a0a0;
--line:#2e2e2e;--accent:#7aa9e0;--chip:#1c1f24}body{background:#121212}}
*{box-sizing:border-box}
body{margin:0;padding:3rem 1.25rem;color:var(--fg);line-height:1.65;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",
"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
main{max-width:44rem;margin:0 auto}
h1{font-size:2rem;margin:0 0 .35rem;letter-spacing:-.02em}
.headline{color:var(--accent);font-weight:600;margin:0 0 .35rem}
.meta{color:var(--muted);font-size:.92rem;margin:0 0 1.75rem}
h2{font-size:.8rem;text-transform:uppercase;letter-spacing:.09em;
color:var(--muted);margin:2.25rem 0 .75rem;font-weight:600}
section{border-top:1px solid var(--line);padding-top:.25rem}
ul{margin:0;padding-left:1.15rem}li{margin:.4rem 0}
.chips{display:flex;flex-wrap:wrap;gap:.4rem;padding:0;list-style:none}
.chips li{margin:0;background:var(--chip);border-radius:999px;
padding:.28rem .7rem;font-size:.85rem}
a{color:var(--accent)}
.links{display:flex;flex-wrap:wrap;gap:1rem;font-size:.95rem}
.seeking{background:var(--chip);border-left:3px solid var(--accent);
padding:.85rem 1rem;border-radius:0 6px 6px 0}
footer{margin-top:3rem;color:var(--muted);font-size:.8rem}
"""


def render(p: dict, skills: list[str]) -> str:
    e = lambda s: html.escape(str(s or ""))                     # noqa: E731
    name, headline = e(p.get("name")), e(p.get("headline"))
    meta = " · ".join(filter(None, [e(p.get("location")), e(p.get("company"))]))

    parts: list[str] = []
    if p.get("seeking"):
        parts.append(f'<section><h2>Currently seeking</h2>'
                     f'<p class="seeking">{e(p["seeking"])}</p></section>')
    if p.get("about"):
        body = "".join(f"<p>{e(x)}</p>"
                       for x in str(p["about"]).strip().split("\n\n") if x.strip())
        parts.append(f"<section><h2>About</h2>{body}</section>")
    if p.get("highlights"):
        li = "".join(f"<li>{e(h)}</li>" for h in p["highlights"])
        parts.append(f"<section><h2>Selected work</h2><ul>{li}</ul></section>")
    if skills:
        li = "".join(f"<li>{e(s)}</li>" for s in skills)
        parts.append(f'<section><h2>Expertise</h2>'
                     f'<ul class="chips">{li}</ul></section>')
    if p.get("credentials"):
        li = "".join(f"<li>{e(c)}</li>" for c in p["credentials"])
        parts.append(f'<section><h2>Credentials</h2>'
                     f'<ul class="chips">{li}</ul></section>')

    links = [f'<a href="{e(u)}" rel="me">{e(k.title())}</a>'
             for k, u in (p.get("links") or {}).items() if u]
    if p.get("email"):
        links.append(f'<a href="mailto:{e(p["email"])}">Email</a>')
    if links:
        parts.append(f'<section><h2>Contact</h2>'
                     f'<div class="links">{"".join(links)}</div></section>')

    # description meta 决定 Google 搜索结果和 AI 摘要里显示的那两行
    desc = e(re.sub(r"\s+", " ", str(p.get("about") or headline))[:300])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} — {headline}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index,follow,max-snippet:-1">
<meta property="og:type" content="profile">
<meta property="og:title" content="{name} — {headline}">
<meta property="og:description" content="{desc}">
<script type="application/ld+json">
{json_ld(p, skills)}
</script>
<style>{CSS}</style>
</head>
<body>
<main>
  <h1>{name}</h1>
  <p class="headline">{headline}</p>
  <p class="meta">{meta}</p>
  {"".join(parts)}
  <footer>Last updated automatically from the live job-market keyword scan.</footer>
</main>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description="生成带结构化数据的个人主页")
    ap.add_argument("--profile", default="ai-governance", help="用哪个方向的技能词表")
    ap.add_argument("--out", default=str(SITE / "index.html"))
    args = ap.parse_args()

    if not PERSONA.exists():
        sys.exit("找不到 persona.yaml —— 先 `cp persona.example.yaml persona.yaml` 并填好内容")
    p = yaml.safe_load(PERSONA.read_text()) or {}
    if not p.get("name"):
        sys.exit("persona.yaml 里的 name 还没填")

    skills = [str(s) for s in (p.get("skills") or [])]
    if not skills:
        skills = skills_from_report(args.profile)
        if not skills:
            print("  提示：还没有 inbound 报告，技能列表为空。"
                  "先跑 `python -m src.inbound`", file=sys.stderr)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(p, skills))
    print(f"✅ {out}（技能 {len(skills)} 个，来自 {args.profile} 词表）")
    print("   上线：仓库 Settings → Pages → Source 选 main / site 目录")


if __name__ == "__main__":
    main()
