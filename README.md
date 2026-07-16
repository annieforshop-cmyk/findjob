# findjob — 每日自动找工作 + 简历/求职信助手

每天自动扫多个招聘平台，**按你简历的真实内容（不是 title）打分排序**，把当日精选岗位**发到你邮箱**；
对你看中的岗位，一条命令生成 **ATS 关键词对齐建议 + 一封自然真诚的 cover letter 草稿**（基于你简历真实内容，不编造）。

全程跑在 **GitHub Actions**，不占用你电脑、不用你每天盯着 LinkedIn 刷。

---

## 它能做 / 不能做（先说清楚）

**打分是两段式**：先用关键词撒大网初筛（便宜），再用 **LLM 语义打分**只对候选深度评估——
读懂 JD 描述的"实际工作内容"是否和你简历吻合，即使用词不同也能识别，这才是"看内容不看 title"。
输出结构化的总分/技能契合/经历契合/一句话理由。没有 OpenAI key 时自动退回纯关键词打分，不影响运行。

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

### 3. 开启定时任务
`.github/workflows/daily-job-search.yml` 已配好每天 UTC 13:00 运行。
- 想改时间：改 workflow 里的 `cron`（用 UTC 时间）。
- 想立刻测一次：仓库 Actions 页 → daily-job-search → **Run workflow**。

---

## 每天你会收到什么

**三封邮件**（每个方向一封），Top N 个岗位。每个岗位带一份多维度分析：
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
config.yaml                    # 共享设置：数据源/AI打分/邮件/阈值
profiles/<方向>/profile.yaml    # 各方向的岗位名/技能/过滤/搜索词（覆盖 config.yaml）
profiles/<方向>/resume.md       # 各方向的简历（事实来源）
docs/job-search-plan.md        # 针对你三个方向的详细找工作方案
src/sources/*.py               # 各平台适配器（含 jsearch = LinkedIn/Indeed 聚合）
src/fetch.py                   # 汇总抓取 + 去重（单个源失败不影响整体）
src/score.py                   # 第一段：关键词匹配打分（初筛）
src/ai_score.py                # 第二段：LLM 语义打分（结构化：总分/契合/理由）
src/digest.py                  # 邮件正文（文本 + HTML）
src/notify_email.py            # SMTP 发送
src/tailor.py                  # OpenAI：ATS 对齐 + cover letter
src/main.py                    # 每日流水线（多 profile）
.github/workflows/             # 每日定时
data/<方向>/                    # 各方向跨天去重状态（自动回写）
```
