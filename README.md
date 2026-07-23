# findjob — 每天一封邮件：今天新出的高匹配 AI Governance 岗

> 只做一件事，做深：**每天扫全网免费岗位源，只把真正围绕「AI 治理 / 责任 AI」
> 且要你这种业务/风控背景来推动的资深岗（≥60 分）推给你。** 美国岗，
> 不用 OpenAI、不花钱，一份干净、准确、当天新鲜的岗位 feed。

每天早上**一封「每日新岗」邮件**：
- 🎯 **今日高匹配 AI 治理岗**：按 Fit Score 排序，**只保留 ≥60 分**——宁缺毋滥。
- 每个岗位带：匹配分、命中理由、地点、**发布日期**、**来源平台**、直达链接；
  同一岗位多地点自动合并成一行。

**不用 OpenAI**：打分完全走本地规则引擎（`src/score.py` 的 focus 路径）——判断岗位
是否**以 AI 治理为中心**（focus 词进标题，或正文出现 ≥2 个），再按"要业务/治理背景
来推动 AI"的信号加权、按职级和新鲜度调整。不需要任何 API key、不会因欠费而失灵。

**只推 60 分以上**是刻意的：与其给你一屏噪音，不如每天几个真正值得投的。
今天没有达标的，就明说"今天没有"，不硬凑。

**投递执行**（可选）：仓库根目录的 [`AGENTS.md`](AGENTS.md) 是给 AI agent
（Claude Code / Codex）的投递 SOP——挑好岗位后对 agent 说"帮我投这个"，它按
海投/精投走流程、自动填低风险字段、缺关键事实停下来问你、**最终提交永远由你确认**。

全程跑在 **GitHub Actions**，不占用你电脑、不用每天盯着刷。

---

## 它怎么保证"准确"（不用 OpenAI）

打分在 `src/score.py`，纯规则、无网络、无 API key。对 AI Governance 方向走 **focus 路径**：

1. **中心性闸门**：岗位必须真的以 AI 治理为中心——focus 词（ai governance / responsible ai
   / ai policy / ai risk / model governance / nist ai rmf / eu ai act…）出现在**标题**，
   或正文里出现 **≥2 个**。只顺嘴提一句 AI 的合规/法务岗直接丢。
2. **业务背景加权**：命中 governance / risk / compliance / policy / framework / audit /
   stakeholder 等信号越多，说明这岗要的正是"懂业务、懂风控的人来推动 AI"——你的画像。
3. **职级调整**：director / head / manager / lead 加分；engineer / scientist / intern 等
   技术或初级岗直接由标题排除。
4. **美国岗过滤 + 新鲜度**：明确写 UK / Singapore / Europe 等的丢；48 小时内 +8、
   三周以上 -6（旧岗多为幽灵岗）。

最后卡 **60 分总线**。所以邮件里出现的，基本都是真·AI 治理、且要你这种背景的美国岗。

> focus 词表、业务信号、排除规则都在 `profiles/ai-governance/profile.yaml`，随时可调。

**数据源（全部免 key，广撒网）：** 公司官网直连（Greenhouse/Lever/Ashby/SmartRecruiters/
Workday，清单在 `career/ats_companies.yaml`）、**The Muse**、RemoteOK、Remotive、Arbeitnow、
We Work Remotely、Jobicy、Hacker News "Who is hiring"。**JSearch / Adzuna** 有免费 key 时自动加入。

**不做：** 自动登录抓 **LinkedIn / Indeed 官网**（反爬 + 使用条款，易封号，刻意不做）。

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

根目录 `config.yaml` 是**共享设置**：数据源开关、`min_score`(60)、`brief.profiles`（每天跑哪些方向）
等，所有方向继承。想加/删方向：复制一个 `profiles/xxx/` 目录改内容即可。

### 2. 在 GitHub 加 Secrets
**只需要邮箱相关的 5 个**（不需要 OpenAI，不需要 RapidAPI）：

| Secret | 必需？ | 说明 |
|---|---|---|
| `SMTP_HOST` | ✅ | 邮件服务器，Gmail 用 `smtp.gmail.com` |
| `SMTP_PORT` | ✅ | `465`（SSL）或 `587`（TLS） |
| `SMTP_USER` | ✅ | 发件邮箱地址 |
| `SMTP_PASS` | ✅ | 邮箱**应用专用密码**（不是登录密码，见下） |
| `EMAIL_TO` | ✅ | 收件邮箱（你自己） |
| `EMAIL_FROM` | 可选 | 默认同 `SMTP_USER` |
| `RAPIDAPI_KEY` / `ADZUNA_*` | 可选 | **不填也能跑**；填了会多两个聚合源（JSearch/Adzuna）。免 key 的源已经够用 |
| `OPENAI_API_KEY` | 不需要 | 打分已改成本地规则引擎，用不到。只有想用 `src.tailor` 生成 cover letter 才需要 |

> **Gmail 应用专用密码**：需先开两步验证，然后到 Google 账号 → 安全 → 应用专用密码，
> 生成一个 16 位密码填到 `SMTP_PASS`。用 `smtp.gmail.com` + 端口 `465`。

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
