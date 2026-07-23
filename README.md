# findjob — 每天一封邮件：市场上今天出的高匹配新岗

> 只做一件事，做深：**每天扫全网免费岗位源，只把和你高度匹配（≥60 分）的
> 新岗推给你。** 没有 target-firm 清单、没有内推、没有公司尽调——就是一份
> 干净、准确、当天新鲜的岗位 feed。

每天早上**一封「每日新岗」邮件**：
- 🎯 **今日高匹配新岗**：三个方向（AI Governance / AI Risk / Internal Audit）
  合并去重，按**综合 Fit Score 排序**，**只保留 ≥60 分**的岗位——宁缺毋滥。
- 每个岗位带：匹配分、技能/职级分项分、一句话匹配理由、薪资区间（JD 有则取）、
  地点、**发布日期**、**来源平台**、直达链接。

**只推 60 分以上**是刻意的：与其给你一屏 0 分噪音，不如每天几个真正值得投的。
今天没有达标的，就明说"今天没有"，不硬凑。

**投递执行**（可选）：仓库根目录的 [`AGENTS.md`](AGENTS.md) 是给 AI agent
（Claude Code / Codex）的投递 SOP——挑好岗位后对 agent 说"帮我投这个"，它按
海投/精投走流程、自动填低风险字段、缺关键事实停下来问你、**最终提交永远由你确认**。

全程跑在 **GitHub Actions**，不占用你电脑、不用每天盯着刷。

---

## 它怎么保证"准确"

**打分两段式**：先用关键词撒大网初筛（便宜），再用 **LLM 语义打分**深度评估——
读懂 JD 描述的"实际工作内容"是否和你简历吻合，即使用词不同也能识别（看内容不看 title）。
没有 OpenAI key 时退回关键词打分（邮件顶部会告警）。

关键词阶段有四道硬闸门，把噪音挡在门外：
- **核心技能门槛**（`profiles/*/core_skills`）：岗位必须命中至少一个"定义这个方向"的词
  （如 internal audit / model risk），光靠 banking、cpa 这类通用词进不来。
- **标题排除**（`exclude_title_keywords`）：sales / customer success / tax 等岗位族按 title 直接排除。
- **美国岗过滤**（`us_only`）：location 明确写 Remote UK / Singapore 等的直接过滤。
- **新鲜度**：48 小时内 +8 分、一周内 +4 分、三周以上 -6 分（新岗转化率高，旧岗多为幽灵岗）。

最后再卡 **60 分总线**。所以邮件里出现的，基本都是真的对得上的岗。

如果某天 AI 语义打分没跑成（key 失效/欠费），邮件顶部会出现**醒目告警**说明原因，
而不是默默退化——看到告警就去修。

**能：** 从一堆公开免费 API 稳定拉岗位：RemoteOK、Remotive、Arbeitnow、
We Work Remotely、Jobicy、Hacker News "Who is hiring"、**The Muse**（专业/企业岗，免 key）、
公司官网直连（Greenhouse/Lever/Ashby/SmartRecruiters/Workday，免 key），
以及可选的 **JSearch**（Google-for-Jobs，聚合 LinkedIn/Indeed/Glassdoor 等，需免费 key）
和 **Adzuna**（需免费 key）。

**不能：** 自动登录抓 **LinkedIn / Indeed 官网**（反爬 + 使用条款，易封号，刻意不做）。

---

## 三步启用

### 1. 简历与方向（多 profile）
每个求职方向是 `profiles/<方向>/` 下的一个目录，各自独立跑、独立发邮件。已内置三套：
`ai-governance`、`internal-audit`、`ai-risk`。

每个目录里：
- `resume.md`：该方向的简历（已按你三份简历填好；也可放 `resume.pdf` 自动抽取，PDF 优先）。
- `profile.yaml`：该方向的 `target_titles` / `skills` / `core_skills`（核心技能门槛）/
  `exclude_keywords` / `exclude_title_keywords`（按标题排除的岗位族）/ `queries`——
  **会覆盖根目录 `config.yaml` 的同名项**。

根目录 `config.yaml` 是**共享设置**：数据源开关、`ai_scoring`、`min_score`(60)、邮件行为等，所有方向继承。
想加/删方向：复制一个 `profiles/xxx/` 目录改内容即可。

### 2. 在 GitHub 加 Secrets
仓库 → Settings → Secrets and variables → Actions → New repository secret，加以下几个：

| Secret | 说明 |
|---|---|
| `OPENAI_API_KEY` | **LLM 语义打分**（决定 60 分线准不准）+ cover letter；没有它会退回关键词打分并在邮件顶部告警 |
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

**一封「每日新岗」邮件**：三个方向合并去重、按综合分排序、**只保留 ≥60 分**的今日新岗。
每个岗位带：
- **匹配分**（≥60）+ 技能/职级/行业/回复概率分项分
- **一句话匹配理由**、**薪资区间**（JD 有则取，无则市场估算）
- **地点**、**发布日期**、**来源平台**、直达链接

阈值在 `config.yaml` 的 `min_score`（默认 60）。想更严就调高、想多看点就调低。

### 数据源
远程板（RemoteOK / Remotive / Arbeitnow / WWR / Jobicy）、HN "Who is hiring"、
**The Muse**（专业岗，免 key）、公司官网直连（ats_boards，免 key，清单在
`career/ats_companies.yaml`）都默认打开；**JSearch / Adzuna** 有 key 时自动加入。
撒网撒得多，靠 60 分门槛保证进邮件的都准。

> JSearch 配额：免费档约 200 次/月，每个 `queries` 词 = 1 次调用。词多了可能超额——
> 超了也不影响，其余源照常跑。

## 对某个岗位深度加工

投某个岗位前，用 tailor 生成 ATS 关键词对齐 + cover letter 草稿：

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...

python -m src.tailor --profile ai-governance "https://…岗位链接"
python -m src.tailor --title "Director, AI Governance" --company "Acme" --desc "粘贴JD" -o out.md
```

生成内容遵守两条硬规则：**只用简历里真实存在的信息**、**自然人话不 AI 味**。

---

## 用法速查

平时你**什么都不用做**——GitHub Actions 每天自动跑、自动发一封「每日新岗」邮件。

- **手动跑一次**：`python -m src.brief`（发邮件）或 `python -m src.brief --dry-run`（只打印）。
- **改门槛**：`config.yaml` 的 `min_score`（默认 60）。
- **改方向/技能/搜索词**：编辑 `profiles/<方向>/profile.yaml`，commit 即生效。
- **改画像（职级/年限/地点）**：编辑 `config.yaml` 的 `candidate:`。
- **投递前加工某岗**：`python -m src.tailor ...`（见上）。

---

## 结构

```
config.yaml                    # 共享设置 + career_goal + fit_weights + brief 配置
profiles/<方向>/profile.yaml    # 各方向的岗位名/技能/过滤/搜索词（覆盖 config.yaml）
profiles/<方向>/resume.md       # 各方向的简历（事实来源）
config.yaml                    # 共享设置：数据源开关、min_score(60)、候选人画像
profiles/<方向>/profile.yaml    # 各方向岗位名/技能/core_skills/过滤/搜索词
profiles/<方向>/resume.md       # 各方向简历（事实来源）
src/brief.py                   # ⭐ 每日新岗邮件（合并去重 + 60 分门槛 + 渲染）
src/main.py                    # 抓取 + 评分流水线（被 brief 复用）
src/fetch.py                   # 汇总抓取 + 去重（单个源失败不影响整体）
src/sources/*.py               # 各平台适配器（themuse / jsearch / ats_boards / 远程板…）
src/score.py                   # 第一段：关键词打分 + core_skills/标题/美国岗/新鲜度闸门
src/ai_score.py                # 第二段：LLM 多维评分 + 加权综合（挂掉会告警）
src/notify_email.py            # SMTP 发送
src/digest.py                  # 单方向邮件正文（legacy，python -m src.main 用）
# ——— 投递 & 面试辅助（可选，非每日邮件的一部分）———
AGENTS.md                      # AI agent 投递 SOP（安全边界 + 五状态模型）
career/candidate_profile.yaml  # 申请表事实来源（TBD 项填一次，处处复用）
career/answer_bank.md          # 申请表常见问题的可复用措辞库
career/ats_companies.yaml      # ats_boards 源要直连的公司清单
career/stories/                # STAR 故事库（tailor/面试复用）
career/interviews/             # 面试题库（每公司一个文件）
career/applications.yaml       # 投递记录（src.track）
src/tailor.py                  # ATS 对齐 + cover letter（自动注入故事库）
src/track.py                   # 投递记录 CLI
src/interview.py               # 面试记录 + 准备包生成
src/research.py                # 公司尽调（仅 interview 用，不进每日邮件）
src/stories.py                 # 故事库加载/按 JD 匹配
docs/job-search-plan.md        # 针对三个方向的找工作方案
.github/workflows/             # 每日定时（跑 src.brief）
data/                          # 跨天去重状态（CI 自动回写）
```
