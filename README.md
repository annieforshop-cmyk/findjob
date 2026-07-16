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

一封邮件，Top N 个岗位，每个带：**AI 匹配分**、公司/地点/来源、**一句话匹配理由 + 技能/经历分项分**、
命中技能、「可如实补充的缺口关键词」，和岗位链接。

把 `config.yaml` 的 `auto_tailor_top` 设成 >0（如 3），邮件会为最强的前几个岗位**直接附上 cover letter 草稿**（点开可见），做到"投递就绪"。默认 0（省钱）。

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
