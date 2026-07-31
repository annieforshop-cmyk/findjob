# Inbound：让猎头 / HR 搜得到你的 20 个办法

> 现在这个仓库解决的是 **outbound**——你每天主动去找岗位。
> 这份文档解决**反方向**：别人（猎头、HR、AI sourcing 工具）在搜的时候，
> 你要出现，而且要排在前面。
>
> 排序按**性价比**（效果 ÷ 你要花的力气）。前 6 条能拿走 80% 的效果，
> 先做完前 6 条再往下看。

---

## 先搞清楚机制：2026 年，猎头到底怎么找到人

这决定了你该优化什么。三件事已经变了：

**1. LinkedIn Recruiter 的默认搜索不再是 boolean。**
现在默认是 **AI-Assisted Search**：猎头用大白话描述岗位，系统自己转成筛选条件。
搜索时间从 15 分钟掉到 30 秒。**后果**：猎头一次搜索看的候选人变少了，
排名前 20 之外基本没人翻——你不是"要被搜到"，是"要排进前 20"。

**2. LinkedIn 上线了 Hiring Assistant（AI agent）。**
它会自己跑几十轮搜索，主动推荐候选人，并且看的不只是关键词匹配，还包括
**职业轨迹（career trajectory）、技能邻接性（skill adjacency）、互动信号（engagement signals）**。
试点数据：每个岗位省 4 小时以上，需要人工过的档案少了 62%。
**后果**：档案静止不动的人会被系统性地降权——"活跃度"从加分项变成了准入项。

**3. AI sourcing 工具已经不只看 LinkedIn。**
hireEZ 这类工具覆盖 45+ 平台、8 亿档案；专业岗位里 **34% 的成功招聘来自
LinkedIn 之外的渠道**。
**后果**：只优化 LinkedIn 等于放弃三分之一的机会。

**排序的三个支柱**（三个都要，缺一个就掉出前排）：
关键词/语义匹配 → 档案完整度 → 活跃度与互动信号。

---

## 第一梯队：先做这 6 条（80% 的效果在这里）

### 1. 用**市场自己的词**重写 Headline，把职位名放最前面

猎头搜 "AI Governance"，命中的是你 Headline 里的字符串。你写
"Director @ Morgan Stanley | 热爱科技"，命中率是零。

跑 `python -m src.inbound` —— 它会从**你自己每天抓的真实 JD** 里统计出
招聘方实际在用的职位短语（当前 ai-governance 方向：`AI Governance` 出现在
13 个岗位标题里，`Model Governance` 3 个），并生成 Headline 候选。

要点：
- 最关键的职位名放**最前面**——搜索结果列表只显示 Headline 前一截；
- 220 字符全用满，用 `|` 分隔塞进 4–6 个高频词；
- 不要写公司内部叫法（"Director, Audit Innovation"），写市场的叫法。

### 2. Skills 板块填满 50 个，且顺序按 JD 频率排

这是**最被低估的一条**。LinkedIn 排序时明确会看三件事：这个技能在不在你的
Skills 列表、有多少 endorsement、以及它是否同时出现在档案别处。三项全中的排最前。
同一个技能，50 个 endorsement 的排在 0 个的前面。

- 50 个名额**全部用掉**（大多数人只填十几个，白送的排名）；
- 前 3 个是"置顶技能"，权重最高——放最高频的那 3 个；
- 顺序直接抄 `reports/<日期>-inbound-<方向>.md` 第 4 节。

### 3. 补齐**缺口词**——你有实力但档案里没写的英文词

`src/inbound.py` 会把 JD 高频词和你的档案做差集。当前 ai-governance 方向跑出来的
高价值缺口（区分度 = 这个词在你这个市场比在别的岗位常见多少倍）：

| 缺口词 | 区分度 | 说明 |
|---|---|---|
| `ai governance framework` | 203× | 你实际就在做，只是简历是中文写的 |
| `nist ai risk` / `nist ai rmf` | 100×+ | 精确术语，猎头会原样搜 |
| `emerging ai` | 36× | |
| `enterprise ai` / `ai system` / `ai adoption` | 20–26× | |
| `ai use case` / `ai agent` / `prompt injection` | 14–100× | |
| `ai safety` / `responsible ai principle` | 34–100× | |

**规则：有 → 立刻加；没有 → 不要编。** 这个表每周会变，跟着重跑。

### 4. 三处重复命中（Headline + About + 经历正文）

LinkedIn 2026 走**语义匹配**，看的是上下文，不是孤立的技能标签。
同一个关键词在 Headline、About、经历描述里都出现，权重远高于只出现一次。

具体做法：挑出你最想被搜到的 6–8 个词（比如 `AI governance`、`EU AI Act`、
`NIST AI RMF`、`model risk`、`responsible AI`），确保每个都在这三处出现过。

### 5. 打开 **Open To Work（仅招聘人员可见）**+ 填满 Career Interests

- 用"仅招聘人员可见"那档，不用绿框——绿框在现任雇主那边有风险，
  而排名收益主要来自前者；
- Career Interests 里的**职位名、地点、开始时间**是 Recruiter 的独立筛选维度，
  留空 = 在这些筛选下直接消失；
- 地点填 **New York + Remote (US)** 两个，别只填一个。

### 6. 每周至少发 1 条、评论 3 条

数据很直接：**每周有发帖/互动的档案，排名高于凭证完全相同但沉寂的档案。**
Hiring Assistant 明确把 engagement signals 算进推荐。

不用写长文。最省力的可持续做法（下面第 14 条会讲怎么自动化）：
- 每周挑 1 条 AI 监管新闻（EU AI Act 落地进度、NIST 更新、SEC/OCC 指引），
  写 3 句你的实操视角；
- 在 3 个 AI governance 领域大 V 的帖子下留有信息量的评论——
  **猎头会直接从"有质量的评论者"里挖人**，这是公开的 sourcing 手法。

---

## 第二梯队：LinkedIn 内部还能挖的（7–12）

### 7. 自定义 URL + 全站可见 + 公开档案开到最大

`linkedin.com/in/你的名字-ai-governance` 这种自定义 URL 直接影响 Google 上
搜你名字的排名。同时把"公开档案"里的每一块（About、经历、技能）都设为公开——
默认设置会挡掉一部分，导致你在 LinkedIn 之外的搜索引擎里是残缺的。

### 8. 攒 endorsement：定向换，不要广撒

前 3 个置顶技能各攒到 **20+ endorsement**。做法：找 15 个真正共事过的同事，
先给对方 endorse 你确知的技能（大部分人会回礼），别群发。

### 9. 3 条 recommendation，每条埋关键词

推荐信正文进入档案的索引文本。请前同事写的时候，直接给他们一句话草稿，
里面自然带上 `AI governance framework`、`AI risk assessment` 这类词。
一条来自 MD/Director 级别的推荐，可信度权重高于三条平级的。

### 10. Featured 区放 3 个作品

Featured 是猎头点进档案后视线第一站，也是"档案完整度"的一项。放：
- 一篇你写的 AI 治理方法论（哪怕就是 LinkedIn 文章）；
- 一张 AI governance 框架图 / 检查清单；
- 一个演讲录像或活动截图（你有"向 200+ 高级领导演讲"的经历，这是强素材）。

### 11. 经历条目里塞**量化战绩**，不是职责描述

"负责 AI 治理框架" vs "为 200+ 高管落地企业级 AI 治理框架，覆盖 X 个 AI 用例的
intake 与持续监控"——后者既多命中关键词，又让猎头点开后愿意联系你。
career trajectory 是 Hiring Assistant 明确会看的维度，把"从审计 → 风险 → AI 治理"
这条上升线在职位描述里写清楚。

### 12. 加对群组 + 关注对的公司

LinkedIn Recruiter 有"群组"和"公司关注者"筛选维度，而且**同群组会提升
connection proximity**（连接距离也是排序因子之一）。加 AI governance / IAPP /
model risk 相关群组，关注你的目标公司——很多猎头会优先从关注者里筛。

---

## 第三梯队：LinkedIn 之外（13–17）—— 34% 的机会在这里

### 13. 建一个**自己的个人主页**，带 schema.org 结构化数据

AI sourcing 工具和 ChatGPT/Perplexity 这类搜索都在爬公开网页。一个
GitHub Pages 静态页（免费）+ `JSON-LD Person` 标记，能让你在
"AI governance director New York" 这类查询里被**直接引用出来**。

这一条我已经建好了工具，见下面「已经建好的东西」。

### 14. 把内容生产自动化，让第 6 条可持续

你已经有每天抓 JD 的 pipeline 了。同一套基础设施可以顺手做内容选题：
从当天的 JD 里提取正在变化的高频词（比如某周 `AI agent governance` 突然从
5% 涨到 20%），那就是这周最该发的选题——**你在写市场当下最缺的东西**，
既踩关键词又真的有信息量。

### 15. 在猎头会去翻的**专业社区**留痕

- **IAPP**（你在自学 AIGP，正好）：论坛发言、拿到证书后进公开名录；
- **Reddit** r/artificial、r/compliance 的实质性回答；
- 行业 Slack / Discord（AI governance 领域有几个活跃的）；
- **Meetup / Luma** 上的 AI governance 线下活动——招聘方会赞助和蹲这些活动。

社区留痕的转化率低于 LinkedIn，但**竞争极小**，且被找到时对方的意向度高得多。

### 16. 主动进"人才库"，而不是等着被搜

- 目标公司的 **Talent Community**（大部分 Workday/Greenhouse 页面底部都有，
  你的 `career/ats_companies.yaml` 里已经有公司清单了）；
- AI governance 垂直猎头公司的候选人库（比这些公司的通用池精准得多）。

这条的本质：把"被搜到"换成"已经在名单里"。

### 17. 写一篇能被引用的东西

一篇扎实的长文（比如"投行落地 EU AI Act 的 12 个控制点"）能同时吃到：
Google 搜索、LinkedIn 内部搜索、AI 搜索引擎引用、以及被同行转发带来的自然曝光。
一篇好文章的半衰期以年计，远长于日常发帖。

---

## 第四梯队：加速与验证（18–20）

### 18. 反向操作：让猎头先认识你

主动加 20 个**专做 AI governance / risk 的猎头**（搜 "AI governance recruiter"、
"GRC executive search"）。不要发求职信息，只说一句"我在这个方向，
以后有合适的可以找我"。猎头的档案库是他们自己的，你进了库就长期有效——
这条绕开了排名机制本身。

### 19. 校友与前同事路径

Morgan Stanley / BNY Mellon / KPMG 的前同事已经散到各家公司了。
内推进来的候选人不走搜索排名，直接进 pipeline。Clark University 校友库同理。
这是**转化率最高**的一条，只是不 scale。

### 20. 建立度量，别凭感觉调

LinkedIn 自带三个数你每周要记：
- **Search appearances**（一周内你出现在多少次搜索里）← 这是第 1–5 条的直接 KPI
- **Profile views** + 查看者的职位（有多少是 recruiter/talent 头衔）
- **InMail 数量**

改档案 → 等两周 → 看这三个数。涨了就沿着方向继续，没涨就换。
**注意：改完档案后 3 天内别频繁再改**，改动期间 LinkedIn 会短暂降权。

---

## 已经建好的东西

### `python -m src.inbound`

从你自己每天抓的真实 JD 里，反推**猎头搜索用的词表**，生成一份关键词处方。

```bash
python -m src.inbound                        # 三个方向全跑
python -m src.inbound --profile ai-governance
```

输出：`reports/<日期>-inbound-<方向>.md`，包含：

1. 招聘方在用的**职位短语**（Headline 该用哪个词）
2. 🔴 **缺口词**——高频出现在 JD、你档案里却没有的（按普及度 × 区分度排序）
3. ✅ 已覆盖词——确认在档案里的位置够靠前
4. **Skills 50 个的填写顺序**
5. Headline 候选（卡 220 字符）
6. About 骨架 + 关键词放置指引

**为什么这个做法比抄网上的"LinkedIn 优化清单"准**：网上的清单是通用的；
这个词表来自**你的目标市场当下真实在招的岗位**，而且用了对照语料算区分度——
`data`、`business`、`team` 这种到处都有的泛词会被自动剔除，留下的是
`ai governance framework`（区分度 203×）、`nist ai rmf`（90×）这种
猎头真的会打进搜索框的词。市场变了，重跑一次词表就跟着变。

工作原理三步：
1. **切语料**：用 `focus_terms` / `core_skills` 把近千份 JD 切成「你的目标市场」
   和「对照背景」两堆；
2. **杀套话**：检测逐字重复出现在大量 JD 里的整句（EEO 声明、公司简介、
   合规模板段落），整句剔除——真术语分散在不同句子里，套话不会，所以这刀砍得准；
3. **算价值**：普及度 × 区分度 × 短语加成，短语优先（猎头搜的是短语不是单词）。

---

## 执行顺序建议

| 周 | 做什么 | 预期 |
|---|---|---|
| 第 1 周 | 跑 `src.inbound`，重写 Headline + Skills 50 + 补缺口词（第 1–4 条） | Search appearances 开始动 |
| 第 2 周 | Open To Work + Career Interests + 自定义 URL + 公开档案（第 5、7 条） | 进入 Recruiter 的筛选范围 |
| 第 3 周 | endorsement + recommendation + Featured（第 8–10 条） | 排名进一步前移 |
| 第 4 周起 | 每周 1 帖 3 评论，长期跑（第 6、14 条） | 活跃度信号，这是复利项 |
| 并行 | 加 20 个猎头 + 校友路径（第 18、19 条） | 绕开排名，直接进人才库 |

第 1 周做完就该能看到 Search appearances 的变化。没变化说明关键词还没对上——
把 `reports/` 里最新那份处方拿出来重新对一遍。

---

## 参考

- [How the LinkedIn Search Algorithm Works in 2026](https://linkedinrank.com/blogs/linkedin-search-algorithm-explained)
- [LinkedIn SEO: How to Optimize Your Profile So Recruiters Find You in 2026](https://blog.theinterviewguys.com/linkedin-seo/)
- [LinkedIn Skills & Endorsements: Rank in Recruiter Searches (2026)](https://cv4me.pro/blog/linkedin-skills-endorsements-strategy)
- [Hiring Assistant for LinkedIn Recruiter & Jobs](https://business.linkedin.com/hire/hiring-assistant)
- [LinkedIn Recruiter AI Features in 2026](https://www.noon.ai/blog/articles/09-linkedin-recruiter-ai-features-2026)
- [LinkedIn Recruiter Search Filters Guide (2026)](https://www.leonar.app/blog/linkedin-recruiter-search-filters/)
- [Source Passive Candidates Without LinkedIn Recruiter](https://www.yena.ai/blog/how-to-source-passive-candidates-without-linkedin-recruiter-2026)
- [12 Hidden Recruiting Platforms Beyond LinkedIn Most Recruiters Miss](https://www.pin.com/blog/sites-like-linkedin-recruiting/)
