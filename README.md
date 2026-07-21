# findjob — Career OS：每天一封 Career Brief，20-30 分钟搞定求职

> **Job Search ≠ Apply More。** Job Search = 精准匹配 + Recruiter + Networking +
> Personal Brand + ATS 优化 + Career Strategy。这个仓库把每一项都自动化。

每天早上**一封 Career Brief 邮件**，包含：
- ⭐ **Dream Company 官网新岗**（Target-50 名单，直连 Greenhouse/Lever/Ashby/Workday 等官方 API，不依赖 LinkedIn）
- 🎯 **Top Jobs**：三个方向合并，按 12 维**综合 Fit Score** 排序（含职业路径分、recruiter 回复概率、裁员风险）
- 🔎 **公司自动尽调**：近期新闻、AI 布局、裁员风险、cover letter 切入点、面试角度
- 🤝 **内推人选**：每个 Top 岗位的校友/前同事/决策者 LinkedIn 精准搜索链接 + 破冰消息草稿
- ⏰ **跟进提醒**：投递 7/14 天无回音自动提醒 follow-up
- 📇 **Recruiter Pipeline**：每周新增 5-10 个猎头连接的执行计划 + 到期关系提醒
- ✍️ **每周一 LinkedIn 帖子草稿**（AI Governance/NIST AI RMF 话题轮换，你的口吻）

配套资产库（`career/`，全部可携带）：**STAR 故事库**（简历/CL/面试复用）、
**Interview Knowledge Base**（每家公司历次面试题沉淀）、申请与人脉 CRM、
**Candidate Profile + Answer Bank**（申请表事实与措辞库，借鉴开源项目 ApplyPilot）。

**投递执行**：仓库根目录的 [`AGENTS.md`](AGENTS.md) 是给 AI agent（Claude Code /
Codex）的投递 SOP——从邮件挑好岗位后，对 agent 说"帮我投这个岗"，它会按
海投/精投两种模式走流程，自动填低风险字段、缺高影响事实就停下来问你、
**最终提交永远由你确认**。每个岗位落入
Submitted / Pending / Skipped / Blocked / Needs-user 五种状态之一（`src.track` 记录）。

**完整手册见 [docs/career-os.md](docs/career-os.md)。** 以下是基础引擎说明。

全程跑在 **GitHub Actions**，不占用你电脑、不用你每天盯着 LinkedIn 刷。

---

## 它能做 / 不能做（先说清楚）

**打分是两段式**：先用关键词撒大网初筛（便宜），再用 **LLM 语义打分**只对候选深度评估——
读懂 JD 描述的"实际工作内容"是否和你简历吻合，即使用词不同也能识别，这才是"看内容不看 title"。
输出结构化的总分/技能契合/经历契合/一句话理由。没有 OpenAI key 时自动退回纯关键词打分，不影响运行。

关键词初筛不只是撒网，还有四道硬闸门（LLM 挂掉时也能保住质量）：
- **核心技能门槛**（`profiles/*/core_skills`）：岗位必须命中至少一个"定义这个方向"的词
  （如 internal audit / model risk），光靠 banking、cpa 这类通用词进不来。
- **标题排除**（`exclude_title_keywords`）：sales / customer success / tax 等岗位族按 title 直接排除。
- **美国岗过滤**（`us_only`）：location 明确写 Remote UK / Singapore 等的直接过滤。
- **新鲜度**：48 小时内 +8 分、一周内 +4 分、三周以上 -6 分（新岗转化率高，旧岗多为幽灵岗）。

如果某天 AI 语义打分没跑成（key 失效/欠费），邮件顶部会出现**醒目告警**说明原因，
而不是默默退化——看到告警就去修，否则排序质量会差很多。

**能：** 从有公开免费 API 的平台稳定拉岗位并智能匹配：
RemoteOK、Remotive、Arbeitnow、We Work Remotely、Jobicy、Hacker News "Who is hiring"，
以及可选的 **Adzuna**（聚合器，含部分 Indeed 来源，需免费 key）。

**不能：** 自动登录并抓 **LinkedIn / Indeed 官网**。它们有反爬和使用条款限制，
自动抓取不稳定且可能封号，本项目刻意不做。LinkedIn 请继续手动用，但把精力留给「申请」而不是「刷」。

**「让别人看到你」** 属于简历/主页 SEO，自动化帮不上——见文末清单。

---

## 三步启用

### 1. 简历与方向（多 profile）
每个求职方向是 `profiles/<方向>/` 下的一个目录，各自独立跑、独立发邮件。已内置三套：
`ai-governance`、`internal-audit`、`ai-risk`。

每个目录里：
- `resume.md`：该方向的简历（已按你三份简历填好；也可放 `resume.pdf` 自动抽取，PDF 优先）。
- `profile.yaml`：该方向的 `target_titles` / `skills` / `exclude_keywords` / `jsearch.queries` /
  `min_score`——**会覆盖根目录 `config.yaml` 的同名项**。

根目录 `config.yaml` 是**共享设置**：数据源开关、`ai_scoring`、邮件行为、`top_n` 等，所有方向继承。
想加/删方向：复制一个 `profiles/xxx/` 目录改内容即可。

### 2. 在 GitHub 加 Secrets
仓库 → Settings → Secrets and variables → Actions → New repository secret，加以下几个：

| Secret | 说明 |
|---|---|
| `OPENAI_API_KEY` | 生成 cover letter / 对齐建议用 |
| `SMTP_HOST` | 邮件服务器，如 Gmail 用 `smtp.gmail.com` |
| `SMTP_PORT` | `465`（SSL）或 `587`（TLS） |
| `SMTP_USER` | 发件邮箱地址 |
| `SMTP_PASS` | 邮箱**应用专用密码**（不是登录密码，见下） |
| `EMAIL_TO` | 收件邮箱（你自己） |
| `EMAIL_FROM` | 可选，默认同 `SMTP_USER` |
| `RAPIDAPI_KEY` | **JSearch 用**（LinkedIn/Indeed/Glassdoor/ZipRecruiter 聚合）。rapidapi.com 免费订阅 JSearch |
| `OPENAI_MODEL` | 可选，默认 `gpt-4o-mini` |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | 可选，启用 Adzuna 时才需要 |

> **Gmail 应用专用密码**：需先开两步验证，然后到 Google 账号 → 安全 → 应用专用密码，
> 生成一个 16 位密码填到 `SMTP_PASS`。用 `smtp.gmail.com` + 端口 `465`。

> **两个最常见的静默故障**（邮件顶部出现 ⚠️ 告警时先查这两项）：
> ① OpenAI 余额用尽（429 insufficient_quota）→ platform.openai.com → Billing 充值；
> ② JSearch 返回 404 → RapidAPI 账号没订阅 JSearch（key 存在≠已订阅），
> 到 rapidapi.com 搜 JSearch 点 Subscribe（免费档即可）。

### 3. 开启定时任务
`.github/workflows/daily-job-search.yml` 已配好每天 UTC 13:00 运行。
- 想改时间：改 workflow 里的 `cron`（用 UTC 时间）。
- 想立刻测一次：仓库 Actions 页 → daily-job-search → **Run workflow**。

---

## 每天你会收到什么

**一封 Career Brief**（内容见文首；想恢复"每方向一封"的旧模式，改跑 `python -m src.main`）。
其中每个岗位带一份多维度分析：
- **AI 匹配分** + 投递建议徽标（建议投 / 可考虑 / 可跳过）
- **技能 / 职级 / 年限** 三个分项分（职级和年限按你的真实画像判断，不被 title 误导）
- **一句话匹配理由**、**薪资区间**（JD 有则取，无则市场估算）、**幽灵岗风险**、**公司简评**
- 命中技能、「可如实补充的缺口关键词」、地点（remote/hybrid/onsite，仅限美国）、链接

打分对你的画像是**多角度**的：内容契合 > title；判断真实职级（senior manager–director 带）；
匹配 ~10 年经验；只保留美国岗（JD 列多地点、含美国即可）；识别幽灵岗；估算薪资。
画像写在 `config.yaml` 的 `candidate:`，可随时调。

把 `config.yaml` 的 `auto_tailor_top` 设成 >0（如 3），邮件会为最强的前几个岗位**直接附上 cover letter 草稿**（点开可见），做到"投递就绪"。默认 0（省钱）。

### 数据源覆盖 & 配额
- **JSearch**（走 Google for Jobs）一个源就覆盖 **LinkedIn / Indeed / Glassdoor / ZipRecruiter / Ladders / Built In / Dice / Wellfound** 等主流板——不用逐站爬。
- **Adzuna** 作第二聚合源补充。
- 注意配额：JSearch 免费档约 200 次/月，每个 `queries` 词 = 1 次调用。三方向共 ~24 词 × 每天 ≈ 超免费档；
  可（a）减少 `queries`，或（b）升 JSearch 便宜付费档，或（c）主要靠 Adzuna（免费档 ~250 次/天，更宽松）。

## 对某个岗位深度加工

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...

python -m src.main                                   # 跑全部 profile
python -m src.main --profile ai-governance           # 只跑一个方向
python -m src.tailor --profile ai-governance 3       # 对该方向今天第 3 个岗位生成对齐+cover letter
python -m src.tailor --profile ai-risk "https://..." # 或按链接
python -m src.tailor --title "Director, AI Governance" --company "Acme" --desc "粘贴JD" -o out.md
```

生成内容遵守两条硬规则：**只用简历里真实存在的信息**、**自然人话不 AI 味**。

---

## 用法速查：我之后要怎么调用这些 agent？

平时你**什么都不用做**——GitHub Actions 每天自动跑、自动发三封邮件。只有想深度加工某个岗位时才动手：

**1) 每日找 job + 多维匹配（自动，也可手动触发）**
- 自动：每天定时跑；或到 GitHub 仓库 Actions 页点 **Run workflow** 立即跑一次。
- 本地手动：`python -m src.main`（全部方向）或 `python -m src.main --profile ai-governance`（单方向）。

**2) 改简历 + 写 cover letter（投某个岗位前用）**
```bash
python -m src.tailor --profile ai-governance 3        # 对该方向今天邮件里第 3 个岗位
python -m src.tailor --profile internal-audit "https://…链接的一部分"
python -m src.tailor --title "IT Audit Director" --company "Acme" --desc "整段粘贴JD" -o out.md
```
输出：① ATS 关键词对齐（哪些词你有、用 JD 的措辞对齐；哪些是缺口）② 一封 cover letter 草稿。
你人肉微调几句 → 用 **Simplify** 浏览器插件自动填表、**你自己点提交**（不做自动投递）。

**3) 调方向/技能/搜索词**：编辑 `profiles/<方向>/profile.yaml`，commit 即生效。
**4) 调你的画像（职级/年限/地点偏好）**：编辑 `config.yaml` 的 `candidate:`。

## 本地手动跑

```bash
python -m src.main --dry-run   # 只打印，不发邮件、不写状态
python -m src.main             # 真正发邮件（需设好 SMTP 环境变量）
```

---

## 让别人主动找到你（自动化之外，但很关键）

1. **LinkedIn 打开 "Open to work"**（可仅对招聘者可见），headline 写清方向+技能关键词，不只写 title。
2. **About / 经历里堆真实关键词**：招聘者搜的是技能词（"A/B testing" "SQL" "causal inference"），把你真有的都写进去。
3. 简历文件名、GitHub、个人站保持一致的关键词，方便被搜索到。
4. 与其每天刷，不如**每天投 3-5 个高匹配岗位**——本工具就是帮你把「找」的时间省下来投在「投」上。

---

## 结构

```
config.yaml                    # 共享设置 + career_goal + fit_weights + brief 配置
profiles/<方向>/profile.yaml    # 各方向的岗位名/技能/过滤/搜索词（覆盖 config.yaml）
profiles/<方向>/resume.md       # 各方向的简历（事实来源）
career/candidate_profile.yaml  # 申请表事实来源（TBD 项填一次，处处复用）
career/answer_bank.md          # 申请表常见问题的可复用措辞库
AGENTS.md                      # AI agent 投递 SOP（安全边界 + 五状态模型）
career/dream_companies.yaml    # ⭐ Target-50 名单（ATS 直连配置）
career/stories/                # STAR 故事库（简历/CL/面试复用）
career/interviews/             # Interview Knowledge Base（每公司一个文件）
career/recruiters.yaml         # Recruiter pipeline CRM
career/network.yaml            # 校友/前同事/目标角色（内推网络）
career/applications.yaml       # 申请跟踪（follow-up 提醒数据源）
docs/career-os.md              # ⭐ 完整使用手册（十大模块）
docs/job-search-plan.md        # 针对你三个方向的详细找工作方案
src/brief.py                   # ⭐ 每日 Career Brief（一封邮件整合一切）
src/dream.py                   # Dream 公司官网监控（Greenhouse/Lever/Ashby/Workday...）
src/research.py                # 公司尽调 agent（新闻 + LLM，缓存14天）
src/network.py                 # Networking agent（内推链接 + recruiter pipeline）
src/track.py                   # 申请/recruiter 跟踪 CLI
src/interview.py               # 面试记录 + 准备包生成
src/branding.py                # 每周 LinkedIn 内容引擎
src/stories.py                 # 故事库加载/按 JD 匹配
src/sources/*.py               # 各平台适配器（含 jsearch = LinkedIn/Indeed 聚合）
src/fetch.py                   # 汇总抓取 + 去重（单个源失败不影响整体）
src/score.py                   # 第一段：关键词匹配打分（初筛）
src/ai_score.py                # 第二段：Fit Score v2 —— 12 维 LLM 评分 + 加权综合
src/digest.py                  # 单方向邮件正文（legacy 模式）
src/notify_email.py            # SMTP 发送
src/tailor.py                  # ATS 对齐 + cover letter（自动注入故事库）
src/main.py                    # 抓取+评分流水线（被 brief 复用；也可单独跑）
.github/workflows/             # 每日定时（跑 src.brief）
data/                          # 去重状态/研究缓存/发帖历史（CI 自动回写）
```
