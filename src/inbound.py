"""Inbound（被动曝光）引擎：让猎头 / HR 搜得到你。

现有 pipeline 解决的是 outbound——你去找岗位。这个模块解决反方向：
**别人搜的时候，你要排在前面。**

核心洞察：招聘方（LinkedIn Recruiter、hireEZ、SeekOut、Juicebox 这类 AI
sourcing 工具）搜候选人用的词，和他们写 JD 用的词是同一套词表。而你的仓库
每天已经在抓这个方向的真实 JD——`data/ats_details.json`（近千份全文）+
`data/<profile>/last_run.json`（当日高分岗，带 title）。

所以：把 JD 语料当成"招聘方词表"来挖，再和你简历/profile 里已有的词做差集，
就得到一份**精确的、有数据支撑的 LinkedIn 关键词处方**——
哪些词必须进 Headline、哪些进 Skills 前 10、哪些是你有实力但档案里没写的缺口。

用法：
  python -m src.inbound --profile ai-governance
  python -m src.inbound --profile ai-governance --top 80
  python -m src.inbound                      # 跑 config.yaml 里 brief.profiles 的全部方向

输出：reports/<date>-inbound-<profile>.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
from collections import Counter
from pathlib import Path

from .main import ROOT, discover_profiles, load_context

DATA = ROOT / "data"
REPORTS = ROOT / "reports"

# LinkedIn 硬限制（2026）——生成建议时按这个卡长度
HEADLINE_MAX = 220
SKILLS_MAX = 50

# 招聘文书里高频但零检索价值的词。不做通用英文停用词表——那会误杀
# "risk" "controls" 这种真正的检索词——只杀 JD 套话。
STOP = set("""
a an the and or of to in for with on at by as is are be been being will would
this that these those from into out over under more most other such not no nor
you your our we us they their its it he she his her him them who whom which
what when where why how all any both each few many some own same so than too
very can just should now if then else while about after before during through
per via within across between among against upon
job jobs position positions role roles opportunity opportunities candidate
candidates applicant applicants employment employer company companies
description responsibilities requirements qualifications preferred required
minimum basic experience experiences year years work working works team teams
ability able strong excellent good great new including include includes
skills skill knowledge understanding demonstrated proven track record
please apply application applications submit resume email careers
equal opportunity employer diversity inclusion veteran disability status
sexual orientation gender identity national origin race color religion age
without regard protected law applicable federal state local reasonable
accommodation background check eligible authorized sponsorship visa
salary compensation range base pay benefits bonus equity insurance medical
dental vision paid time off pto holiday 401k plan plans
full time part time hybrid remote onsite office location locations us usa
united states city new york san francisco london amount
we're you'll we'll it's don't looking seeking join help make like well
support supporting supported provide providing provided ensure ensuring
ensures drive driving drives lead leading leads build building builds
develop developing develops manage managing manages deliver delivering
across levels level day days week weeks month months
re ll ve don doesn isn aren won didn couldn wouldn shouldn hasn haven
world mission passionate exciting fast-moving fast paced hands-on
faster better best top leading world-class cutting-edge state-of-the-art
use using used need needs needed want wants define defines defining
operate operates operating translate translates translating
serve serves serving impact impacts people person one two three
practice practices thing things something anything everything
""".split())

# 行业缩写：.title() 会把它们写成 "Ai Governance" "Eu Ai Act"，
# 在 Headline / Skills / 结构化数据里都是错的，猎头一眼看出是机器生成的
ACRONYM = {
    "ai": "AI", "ml": "ML", "eu": "EU", "us": "US", "uk": "UK", "it": "IT",
    "nist": "NIST", "rmf": "RMF", "iso": "ISO", "iec": "IEC", "soc": "SOC",
    "cpa": "CPA", "aigp": "AIGP", "cia": "CIA", "cisa": "CISA", "cfa": "CFA",
    "sox": "SOX", "coso": "COSO", "pcaob": "PCAOB", "icfr": "ICFR",
    "sec": "SEC", "occ": "OCC", "gdpr": "GDPR", "ccpa": "CCPA",
    "grc": "GRC", "llm": "LLM", "llms": "LLMs", "nlp": "NLP", "api": "API",
    "genai": "GenAI", "saas": "SaaS", "mlops": "MLOps", "kyc": "KYC",
    "aml": "AML", "vp": "VP", "svp": "SVP", "evp": "EVP", "md": "MD",
    "gaap": "GAAP", "ifrs": "IFRS", "erm": "ERM", "mrm": "MRM",
}


def smart_title(term: str) -> str:
    """Title Case，但缩写保持全大写。"""
    return " ".join(ACRONYM.get(w, w.title()) for w in term.split())


MID_STOP = set(
    "to with and or the a an for in on by as is are be been from that which "
    "you your our their its it we they this these those will would can".split())

# 词形归一：让 "controls"/"control"、"frameworks"/"framework" 计到一起
_PLURAL = re.compile(r"(?<=[a-z]{3})s$")
_TOKEN = re.compile(r"[a-z][a-z0-9+/&.\-]*")
# 断句/断句子成分——n-gram 不允许跨这些边界，避免拼出 "compliance we" 这种噪音
_SPLIT = re.compile(r"[^a-z0-9+/&.\-']+")


# -es 只在这些词干后面才是真复数后缀（processes→process, boxes→box）；
# "cases" 的词干是 case 不是 cas，所以单个 s 不算——否则会切出 "use cas"
_ES_STEM = ("ss", "x", "z", "ch", "sh")


# 这些词的 -s 不是复数，砍掉就成了 "data analytic"
NO_STEM = {"analytics", "operations", "communications", "logistics", "ethics",
           "economics", "statistics", "politics", "physics", "mathematics",
           "sales", "news", "series", "means", "aws", "ops", "devops",
           "services"}   # "financial services" 不该显示成 "financial service"


def _singular(w: str) -> str:
    # 长度 <5 不动词形：bias→bia、saas→saa 这种误伤比漏归一更糟
    if len(w) < 5 or w in NO_STEM or w.endswith(("ss", "us", "is")):
        return w
    if w.endswith("es") and w[:-2].endswith(_ES_STEM):   # processes -> process
        return w[:-2]
    if w.endswith("ies") and len(w) > 4:   # policies -> policy
        return w[:-3] + "y"
    return _PLURAL.sub("", w)


_SMART = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})


def _clauses(text: str) -> list[list[str]]:
    """切成子句——每个子句是一串 token，标点处断开（n-gram 不跨子句）。"""
    out = []
    for raw in re.split(r"[.;:!?()\[\]•\n\r|,/]+", text.lower().translate(_SMART)):
        toks = [t for t in _SPLIT.split(raw) if t and _TOKEN.fullmatch(t)]
        if toks:
            out.append(toks)
    return out


def boilerplate(docs: list[str], ratio: float = 0.06) -> set[str]:
    """找出样板句——**逐字**出现在大量 JD 里的整句。

    大公司会把同一段模板贴进几十个岗位（EEO 声明、公司简介、
    "regulators rely on us to..." 这种合规套话）。这些句子会让里面的词组
    冲到词表顶部，但它们跟这个岗位要什么人毫无关系。

    判据是「同一句话出现在多少份 JD 里」，不是「某个词出现多少次」——
    真正的术语会分散在**不同的**句子里，样板句不会。所以这一刀砍得掉套话，
    砍不掉真词。
    """
    df: Counter[str] = Counter()
    for d in docs:
        df.update({" ".join(toks) for toks in _clauses(d) if len(toks) >= 5})
    cut = max(3, ratio * max(len(docs), 1))
    return {c for c, k in df.items() if k > cut}


def ngrams(text: str, n_max: int = 3, drop: set[str] | None = None) -> set[str]:
    """一份 JD 里出现过的 1~3 gram 集合（去重 —— 我们要的是文档频率 DF）。"""
    seen: set[str] = set()
    for toks in _clauses(text):
        if drop and " ".join(toks) in drop:
            continue
        toks = [_singular(t) for t in toks]
        for n in range(1, n_max + 1):
            for i in range(len(toks) - n + 1):
                gram = toks[i:i + n]
                # 首尾是套话词的 n-gram 没检索价值
                if gram[0] in STOP or gram[-1] in STOP:
                    continue
                # 中间夹功能词的多半是 JD 套话句子的碎片
                # （"regulation to properly"），不是一个可检索的术语。
                # 特意放行 of —— "line of defense" "conflict of interest" 是真术语
                if any(t in MID_STOP for t in gram[1:-1]):
                    continue
                if any(len(t) < 2 for t in gram):
                    continue
                if all(t.isdigit() for t in gram):
                    continue
                seen.add(" ".join(gram))
    return seen


# ---------------------------------------------------------------- 语料
def _focus_hits(text: str, focus: list[str]) -> int:
    low = text.lower()
    return sum(1 for f in focus if f and f.lower() in low)


def relevance_terms(cfg: dict) -> list[str]:
    """判定"这份 JD 属不属于我这个市场"的词。

    ai-governance 有 focus_terms（score.py 的 focus 路径要用）；internal-audit /
    ai-risk 这类方向没有 focus_terms，它们靠 core_skills 当闸门——这里跟着走
    同一套定义，保证三个方向都能切出干净的目标语料和对照语料。
    """
    for key in ("focus_terms", "core_skills", "target_titles"):
        terms = [str(t) for t in (cfg.get(key) or []) if str(t).strip()]
        if terms:
            return terms
    return []


def load_corpus(namespace: str, cfg: dict) -> tuple[list[str], list[str], list[str]]:
    """返回 (目标市场 JD, 背景 JD, 职位名称)。

    - **目标市场 JD**：真的围绕这个方向的岗位（focus 词命中 ≥2）。
    - **背景 JD**：其余的岗位。用来做对照——"data" "business" 这种词在背景里
      一样满天飞，说明它没有区分度，不是猎头会拿来搜你的词；而 "ai governance"
      "model risk" 只在目标市场里高频，那才是要抢的词。
    - **职位名称**：只保留真的落在你目标职位族里的，避免噪音污染 Headline 建议。
    """
    focus = relevance_terms(cfg)
    titles_cfg = [str(t).lower() for t in (cfg.get("target_titles") or [])]
    docs: list[str] = []
    background: list[str] = []
    titles: list[str] = []
    seen_text: set[int] = set()

    def _relevant_title(t: str) -> bool:
        tl = t.lower()
        return any(tt in tl for tt in titles_cfg) or _focus_hits(tl, focus) > 0

    lr = DATA / namespace / "last_run.json"
    if lr.exists():
        for j in json.loads(lr.read_text() or "[]"):
            d = (j.get("description") or "").strip()
            t = (j.get("title") or "").strip()
            if t and _relevant_title(t):
                titles.append(t)
            if d and hash(d[:400]) not in seen_text:
                seen_text.add(hash(d[:400]))
                docs.append(f"{t}\n{d}")

    det = DATA / "ats_details.json"
    if det.exists():
        blob = json.loads(det.read_text() or "{}")
        for url, v in blob.items():
            d = (v.get("d") if isinstance(v, dict) else str(v)) or ""
            if len(d) < 300 or hash(d[:400]) in seen_text:
                continue
            seen_text.add(hash(d[:400]))
            # 相关性闸门，和 score.py 的 focus 路径同一套逻辑
            if focus and _focus_hits(d, focus) < 2:
                background.append(d)
                continue
            docs.append(d)
            slug = _title_from_url(url)
            if slug and _relevant_title(slug):
                titles.append(slug)

    return docs, background, titles


_WD_SLUG = re.compile(r"/job/[^/]+/([A-Za-z0-9\-]+?)(?:_[A-Z0-9\-]+)?/?$")


def _title_from_url(url: str) -> str:
    """Workday 这类 URL 里带职位 slug，能白捡一批真实职位名。"""
    m = _WD_SLUG.search(url or "")
    if not m:
        return ""
    s = m.group(1).replace("--", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s if 4 <= len(s) <= 70 else ""


# ---------------------------------------------------------------- 打分
def rank_terms(docs: list[str], background: list[str],
               top: int = 120) -> list[tuple[str, int, float]]:
    """返回 [(词, 目标语料文档频次, 区分度 lift)]，按检索价值排序。

    检索价值 = 在目标市场 JD 里的普及度 × 相对背景语料的区分度。
    只按频率排会被 "data"/"business"/"team" 这类满天飞的词淹没——它们在背景
    语料里频率一样高，lift≈1，猎头不会拿它们搜人；真正值钱的是
    "ai governance" "nist ai rmf" 这种只在这个市场高频的词。
    """
    # 两个语料分别检测：目标语料只有几十份，混进背景的近千份里算比例，
    # 一家公司复制到十几个岗位的模板段落会被稀释到阈值以下，抓不出来。
    boiler = boilerplate(docs) | boilerplate(background)
    df: Counter[str] = Counter()
    for d in docs:
        df.update(ngrams(d, drop=boiler))
    bg: Counter[str] = Counter()
    for d in background:
        bg.update(ngrams(d, drop=boiler))

    n, nb = max(len(docs), 1), max(len(background), 1)
    scored: list[tuple[str, int, float]] = []
    for t, c in df.items():
        # 太罕见（<8%）的词没有检索价值
        if c < max(3, 0.08 * n):
            continue
        p = c / n
        q = (bg.get(t, 0) + 0.5) / (nb + 0.5)      # 加性平滑，避免除零
        lift = p / q
        words = len(t.split())
        # 单词要有明显区分度才留（泛词全靠这条挡掉）；多词短语门槛放宽——
        # 短语本身就更精确，而且猎头搜索框里打的基本都是短语
        if words == 1 and lift < 2.5:
            continue
        if lift < 1.3:
            continue
        scored.append((t, c, lift))

    # 排序键：普及度 × log(区分度) × 短语加成
    scored.sort(key=lambda x: -(x[1] / n) * math.log(x[2] + 1)
                * (1.0 + 0.35 * (len(x[0].split()) - 1)))
    return _prune_redundant(scored)[:top]


def _prune_redundant(ranked: list[tuple[str, int, float]]) -> list[tuple[str, int, float]]:
    """去掉被长短语吃掉的短词：如果 governance 的出现几乎都来自
    ai governance，就只留长的那个——LinkedIn 2026 走语义匹配，
    长尾精确短语比泛词更能把你定位出来。"""
    by_term = {t: c for t, c, _ in ranked}
    out = []
    for t, c, lift in ranked:
        longer = [c2 for t2, c2 in by_term.items()
                  if t2 != t and len(t2) > len(t) and f" {t} " in f" {t2} "]
        if longer and max(longer) >= 0.75 * c:
            continue
        out.append((t, c, lift))
    return out


def owned_terms(cfg: dict, resume: str) -> set[str]:
    """你"已经有"的词 = profile.yaml 里声明的 + 简历正文里真实出现的。"""
    own: set[str] = set()
    for key in ("skills", "focus_terms", "business_signals", "core_skills"):
        own |= {str(s).lower().strip() for s in (cfg.get(key) or [])}
    own = {o for o in own if o}
    # 归一化成和 ngrams() 同一套词形，否则 "controls" vs "control" 会误判成缺口
    own |= {" ".join(_singular(w) for w in o.split()) for o in own}
    return own | _resume_phrases(resume.lower())


def _resume_phrases(low: str) -> set[str]:
    """简历里已经出现的 1~3 gram —— 算作"你已经有的词"。"""
    return ngrams(low)


def gap_analysis(ranked: list[tuple[str, int, float]], own: set[str], n_docs: int):
    """把招聘方词表切成两堆：你已覆盖的 / 你缺的。"""
    covered, gaps = [], []
    for t, c, lift in ranked:
        pct = round(100 * c / max(n_docs, 1))
        (covered if t in own else gaps).append((t, pct, lift))
    return covered, gaps


# ---------------------------------------------------------------- 输出
def title_phrases(titles: list[str], cfg: dict) -> list[tuple[str, int]]:
    """招聘方实际在用的**职位短语**（不是完整 title）。

    完整 title 几乎每个都独一无二（"Sr Specialist, Data & AI Governance"），
    统计它没意义。有意义的是里面反复出现的那个短语——那才是猎头会打进
    搜索框的词。"""
    tc: Counter[str] = Counter()
    wanted = [str(t).lower() for t in (cfg.get("target_titles") or [])]
    for raw in titles:
        tl = re.sub(r"\s+", " ", raw.lower()).strip()
        for tt in wanted:
            if tt in tl:
                tc[tt] += 1
    return tc.most_common()


def suggest_headlines(tphrases: list[tuple[str, int]], covered: list) -> list[str]:
    """生成 Headline 候选。规则：最高频的职位名要放在**最前面**——
    搜索结果列表只显示 Headline 的前一截，猎头扫的就是那一截。"""
    tops = [t for t, _ in tphrases[:4]] or ["ai governance"]
    top_terms = [t for t, _, _ in covered[:25]]
    out = []
    for tt in tops[:3]:
        h = f"Director, {smart_title(tt)}"
        # 220 字符是白送的检索面积，能塞就塞满——每多一个词就多一次被搜到的机会
        for x in dict.fromkeys(top_terms):
            if x in tt or tt in x or smart_title(x) in h:
                continue
            nxt = f"{h} | {smart_title(x)}"
            if len(nxt) > HEADLINE_MAX:
                break
            h = nxt
        out.append(h)
    return out


def build_report(profile: str, label: str, cfg: dict, resume: str,
                 top: int = 160) -> str:
    docs, background, titles = load_corpus(profile, cfg)
    n = len(docs)
    ranked = rank_terms(docs, background, top=top)
    own = owned_terms(cfg, resume)
    covered, gaps = gap_analysis(ranked, own, n)
    tphrases = title_phrases(titles, cfg)

    today = dt.date.today().isoformat()
    L: list[str] = []
    a = L.append
    a(f"# Inbound 关键词处方 — {label}")
    a("")
    a(f"> 生成日期 {today} ｜ 目标市场语料 **{n} 份** JD ｜ 对照背景语料 **{len(background)} 份**")
    a(">")
    a("> 招聘方搜候选人用的词 = 他们写 JD 用的词。排序不是单纯看频率，而是")
    a("> **普及度 × 区分度**：一个词要在这个市场里够常见，同时在别的岗位里**不**常见，")
    a("> 才是猎头会真的打进搜索框的词。（所以 data / business / team 这类满天飞的")
    a("> 泛词已被对照语料自动剔除。）")
    a("")

    a("## 1. 招聘方在用的职位名（Headline 用他们的词，不是你公司的内部叫法）")
    a("")
    a("完整 title 几乎个个不重样，没统计意义；下面是**反复出现的职位短语**——")
    a("猎头搜索框里打的就是这些。")
    a("")
    a("| 职位短语 | 出现在几个岗位标题里 |")
    a("|---|---|")
    for t, c in tphrases[:20]:
        a(f"| {smart_title(t)} | {c} |")
    if not tphrases:
        a("| （当前语料里没匹配到 target_titles，先跑一次 `python -m src.main` 攒数据） | — |")
    a("")

    a("## 2. 🔴 缺口词 —— 高频出现在 JD、但你的简历/profile 里没有")
    a("")
    a("这是**最高优先级**。每一个都要判断：我到底有没有这个实力？")
    a("有 → 立刻加进 LinkedIn（Skills / About / 经历描述），这是你现在搜不到的原因。")
    a("没有 → 忽略，**不要编**。")
    a("")
    a("| 关键词 | 出现在 % 的目标 JD | 区分度 | 建议放置位置 |")
    a("|---|---|---|---|")
    for t, pct, lift in gaps[:45]:
        # 位置同时看普及度和区分度：一个只在这个市场出现的精确短语
        # （区分度 200×）哪怕只在 18% 的 JD 里，也比一个 60% 的泛词值钱
        slot = ("Headline + Skills 前 10" if (pct >= 35 or lift >= 25)
                else "Skills + About" if (pct >= 15 or lift >= 8)
                else "经历描述正文")
        a(f"| `{t}` | {pct}% | {lift:.1f}× | {slot} |")
    a("")
    a("> 你的 `resume.md` 是中文写的，所以英文词形匹配不上——**上面很多「缺口」")
    a("> 其实你有，只是档案里没用英文写出来**。这恰恰是问题所在：猎头搜的是英文。")
    a("> 确认自己有的，顺手补进 `profiles/<方向>/profile.yaml` 的 `skills`，")
    a("> 下次跑就不会再报成缺口。")
    a("")

    a("## 3. ✅ 已覆盖词 —— 你有，但要确认在档案里的**位置够靠前**")
    a("")
    a("LinkedIn 2026 的排序会看：这个词在不在 Skills 列表里、有多少 endorsement、")
    a("以及是否在 Headline/About/经历里重复出现。三处都命中的排最前。")
    a("")
    a("| 关键词 | 出现在 % 的目标 JD | 区分度 |")
    a("|---|---|---|")
    for t, pct, lift in covered[:40]:
        a(f"| `{t}` | {pct}% | {lift:.1f}× |")
    a("")

    a(f"## 4. Skills 板块排序建议（LinkedIn 上限 {SKILLS_MAX} 个）")
    a("")
    a("按 JD 频率从高到低填。前 3 个是「置顶技能」，权重最高——把最高频的放这里。")
    a("")
    covered_set = {t for t, _, _ in covered}
    ordered = [t for t, _, _ in covered] + [t for t, _, _ in gaps]
    for i, t in enumerate(ordered[:SKILLS_MAX], 1):
        mark = "" if t in covered_set else "  ← 缺口，确认你确实有再加"
        a(f"{i}. {smart_title(t)}{mark}")
    a("")

    a("## 5. Headline 候选（≤220 字符）")
    a("")
    for h in suggest_headlines(tphrases, covered):
        a(f"- `{h}`  （{len(h)} 字符）")
    a("")
    a("> 上面是**把 220 字符塞满**的版本——检索面积最大，但一眼看过去像关键词堆砌。")
    a("> 词是按价值从左往右排的，所以**从右边往回删**到你觉得像人写的为止")
    a("> （通常留 6–8 个词、120 字符左右是检索和观感的平衡点）。")
    a("> 另外：搜索结果列表只显示 Headline 的**前一截**，最关键的职位名必须放最前面。")
    a("")

    a("## 6. About 骨架（关键词密度 + 可读性）")
    a("")
    a("LinkedIn 的 About 前 3 行是折叠前可见区，也是语义匹配权重最高的一段。结构：")
    a("")
    a("1. **第 1 行 = 你是谁 + 最高频职位名**（把上面第 1 节的 Top 1 职位名原样写进去）")
    a("2. **第 2–3 行 = 三个量化战绩**（数字比形容词更能让猎头停下来）")
    top10 = [smart_title(t) for t, _, _ in covered[:10]]
    a(f"3. **中段 = 关键词块**，自然嵌入这些高频词：{', '.join(top10)}")
    a("4. **结尾 = 一句明确的 CTA**（你在看什么方向、怎么联系你）——")
    a("   猎头看到明确 CTA 的回复率显著高于没有的")
    a("")

    a("## 7. 怎么用这份处方")
    a("")
    a("- 这份报告每周重跑一次，词表会跟着市场变（比如 EU AI Act 落地阶段变化，")
    a("  JD 里的高频词会整体迁移）。你的档案跟着改，就一直踩在猎头的搜索词上。")
    a("- **改完档案后关掉 3 天再打开** —— 频繁改动期间 LinkedIn 会短暂降权。")
    a("- 缺口词里凡是你确实做过的，优先改到**经历条目正文**里，")
    a("  因为语义匹配看的是上下文，不是孤立的技能标签。")
    a("")
    a("---")
    a("")
    a("_完整的 20 条被动曝光策略见 [`docs/inbound-visibility.md`](../docs/inbound-visibility.md)_")
    return "\n".join(L)


def run(profile: str, top: int = 160) -> Path:
    cfg, resume, ns, label = load_context(profile)
    md = build_report(ns, label, cfg, resume, top=top)
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"{dt.date.today().isoformat()}-inbound-{ns}.md"
    out.write_text(md)
    return out


def _md_to_html(md: str) -> str:
    """够用的 Markdown→HTML：标题、表格、加粗、代码、列表。

    不引第三方依赖——这份报告的结构是我们自己生成的，就这几种元素。
    """
    out: list[str] = []
    in_table = False

    def inline(t: str) -> str:
        t = (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        t = re.sub(r"`([^`]+)`", r'<code style="background:#f2f4f7;padding:1px 5px;'
                                r'border-radius:4px;font-size:92%">\1</code>', t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
        return t

    for line in md.splitlines():
        st = line.strip()
        is_row = st.startswith("|") and st.endswith("|")
        if in_table and not is_row:
            out.append("</table>")
            in_table = False
        if is_row:
            cells = [c.strip() for c in st.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue                       # 表格分隔线
            if not in_table:
                out.append('<table cellspacing="0" cellpadding="6" '
                           'style="border-collapse:collapse;font-size:13px;margin:8px 0">')
                in_table = True
                tag, style = "th", "background:#f6f8fa;text-align:left"
            else:
                tag, style = "td", ""
            out.append("<tr>" + "".join(
                f'<{tag} style="border:1px solid #e3e6ea;{style}">{inline(c)}</{tag}>'
                for c in cells) + "</tr>")
            continue
        if m := re.match(r"^(#{1,6})\s+(.*)", st):
            n = len(m.group(1))
            out.append(f'<h{n} style="margin:18px 0 6px">{inline(m.group(2))}</h{n}>')
        elif st.startswith(">"):
            out.append('<blockquote style="border-left:3px solid #d0d7de;margin:8px 0;'
                       f'padding:2px 12px;color:#555">{inline(st.lstrip("> "))}</blockquote>')
        elif re.match(r"^\d+\.\s", st) or st.startswith("- "):
            out.append(f'<div style="margin:2px 0 2px 14px">{inline(st)}</div>')
        elif not st:
            out.append("<div style='height:6px'></div>")
        else:
            out.append(f"<p style='margin:6px 0'>{inline(st)}</p>")
    if in_table:
        out.append("</table>")
    return ("<div style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',"
            "Roboto,'PingFang SC','Microsoft YaHei',sans-serif;line-height:1.6;"
            "max-width:760px;color:#111\">" + "\n".join(out) + "</div>")


def email_reports(paths: list[Path]) -> None:
    from . import notify_email
    md = "\n\n---\n\n".join(p.read_text() for p in paths)
    subject = (f"[findjob · Inbound] {dt.date.today().isoformat()} · "
               f"本周关键词处方（{len(paths)} 个方向）")
    notify_email.send(subject, md, _md_to_html(md))


def main() -> None:
    ap = argparse.ArgumentParser(description="生成 LinkedIn / 被动曝光关键词处方")
    ap.add_argument("--profile", help="方向名（默认跑全部）")
    ap.add_argument("--top", type=int, default=160, help="词表长度")
    ap.add_argument("--email", action="store_true", help="把报告发到 EMAIL_TO")
    args = ap.parse_args()

    targets = [args.profile] if args.profile else discover_profiles()
    outs = []
    for p in targets:
        out = run(p, top=args.top)
        outs.append(out)
        print(f"✅ {p} → {out}")
    if args.email and outs:
        email_reports(outs)
        print(f"📧 已发送 {len(outs)} 份报告")


if __name__ == "__main__":
    main()
