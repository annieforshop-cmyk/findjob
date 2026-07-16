# 找工作方案 — AI Governance / Internal Audit / AI Risk

> 基于你三份简历 + LinkedIn 制定（已去除个人信息）。目标：用最少的时间/精力，
> 让**对的岗位找到你**、也让**你高效找到对的岗位**，并且每一次申请都精准、真诚、过 ATS。

---

## 0. 先认清你的独特优势（定位）

市面上有三类人，但**同时具备三者的人极少**——你就是那少数：

1. **CPA + 10 年大行内部审计/企业风险**（Morgan Stanley Director、BNY Mellon VP、KPMG/BDO）——硬资历、监管语言（SOX/COSO/PCAOB/broker-dealer）。
2. **真实的 AI 治理框架经验**（NIST AI RMF、EU AI Act、ISO 42001、模型风险、AI 治理委员会、AI onboarding/监控）。
3. **动手用 GenAI/Agentic AI**（向 200+ 高管演讲用例、自建 dashboard/AI agent 工具、Claude Code/Copilot）。

> **战略结论**：你最高杠杆的方向是 **金融/受监管行业的 AI Governance**。行业报告显示，
> 同时懂**隐私+AI 治理**的人总薪酬中位数约 **$170k**，只懂 AI 治理约 **$152k**，
> 领导岗（Director/VP/Head）区间 **$195k–270k**——你的资历正好卡在这个高价值交集里。
> Internal Audit 是你的**基本盘/保底**，AI Risk 是**邻近拓展**。三条线并行，但 AI Gov 优先投入。

---

## 1. 三个方向：目标职位 + 目标雇主 + 去哪找

### A. AI Governance（优先）
- **目标职位**：Director/Head/VP of AI Governance；Responsible AI Lead；AI Governance & Risk Manager；AI Policy/Compliance Lead。
- **目标雇主**：大型银行/资管/保险（受监管、最认你的金融背景）；四大及咨询（Deloitte/PwC/EY/KPMG 的 Responsible AI / AI Assurance 团队）；大型科技公司的 AI governance/trust 团队；AI 公司的 policy/governance 岗。
- **去哪找**：
  - 垂直板：**ai-governance-jobs.com / GRC-Careers**（专做 AI 治理/GRC）、**IAPP 职位板**、**ISACA Career Center**。
  - 通用：LinkedIn、**Ladders（$100k+ 高级岗）**、Indeed/Glassdoor（经 JSearch 自动拉）。

### B. Internal Audit（保底）
- **目标职位**：Internal Audit Director/Sr Manager；IT Audit Director；Audit VP（金融）；Head of Audit（中型机构）。
- **目标雇主**：投行/资管/银行/保险的内审部；四大 Internal Audit & Financial Advisory。
- **去哪找**：**IIA（内部审计师协会）Audit Career Center**、**ISACA**（IT 审计/CISA）、**eFinancialCareers**、LinkedIn、Ladders。

### C. AI Risk（拓展）
- **目标职位**：AI Risk Manager/Director；(AI) Model Risk；Technology Risk（AI 方向）；AI Risk & Controls。
- **目标雇主**：银行的 Model Risk Management / Technology Risk；咨询的 AI risk；金融科技风险团队。
- **去哪找**：同 A + 银行官网 careers（Model Risk 常直招）。

> 三个方向的 `target_titles / skills / jsearch.queries` 已分别配在 `profiles/*/profile.yaml`，
> 系统每天分别拉取、分别打分、分别发你一封精选邮件。

---

## 2. ATS 关键词地图（用魔法打败魔法）

第一轮多是 AI/ATS 筛简历。原则：**只写你真有的，但用招聘 JD 的原词**。`src/tailor.py` 会针对具体 JD 帮你对齐；下面是每个方向的"必须出现"高频词，确保你的简历/LinkedIn 里有：

| 方向 | 高频 ATS 关键词（你都真实具备） |
|---|---|
| AI Governance | AI governance, responsible AI, NIST AI RMF, EU AI Act, ISO/IEC 42001, AI risk assessment, model risk, AI policy, governance framework, continuous monitoring, regulatory compliance |
| Internal Audit | internal audit, risk-based audit, SOX, COSO, PCAOB, control testing, audit plan, remediation, regulatory reporting, IT audit, financial services |
| AI Risk | AI risk management, AI RMF, model risk, risk guardrails, responsible AI, controls, continuous monitoring, remediation roadmap, technology risk |

**小抓手**：JD 里出现、你简历没写的词，邮件里会标成"缺口·可如实补充"。你有的就补进去（换成 JD 的措辞），没有的**别硬编**。

---

## 3. 让别人主动找到你（被动流量，很关键）

1. **LinkedIn 打开 "Open to work"**（可设为仅招聘者可见），减少海投、增加 inbound。
2. **Headline 用关键词不用 title**：例如
   `AI Governance & Responsible AI Leader | Internal Audit Director | NIST AI RMF · EU AI Act · Model Risk | CPA | Financial Services`。
3. **About + 经历堆真实关键词**：招聘官是按技能词搜人的（"AI governance" "NIST AI RMF" "model risk" "SOX"），把你真有的都写进去。
4. **完成 AIGP 认证**（IAPP，AI 治理的锚定证书，Body of Knowledge 已更新到含 agentic AI）——你在自学，考下来会显著提升 inbound 和过筛率。可选再加 **CIPP/CIPM**（隐私，能触达"隐私+AI 治理"那档更高薪岗）或 **CRISC/CISA**（风险/IT 审计）。
5. 关注并互动目标公司的 AI governance / audit 领导，内推路径优先。

---

## 4. 每周节奏（省时间、保质量，别海投）

对你这种**资深专业岗，质量 >> 数量**。建议每周固定 2–3 个时段，别每天刷：

- **每天（0 分钟人力）**：系统自动发你 3 封精选邮件（三个方向），你通勤时扫一眼。
- **每周 2 次 × 30 分钟**：挑出 5–8 个真感兴趣的岗位 → 每个跑 `python -m src.tailor --profile <方向> <序号>` 生成 ATS 对齐 + cover letter 草稿 → 你花几分钟人肉微调（加真诚的一句、去掉任何不属实的话）→ 用 **Simplify** 自动填表、你点提交。
- **每周 1 次 × 30 分钟**：给 2–3 个高匹配岗位找**内推**（LinkedIn 搜目标公司的前同事/校友）。资深岗内推转化率最高。
- **忌**：LazyApply 那种"每天投 1500 份"——对你是毒药，会被 ATS 和招聘官识别为垃圾申请、还可能被 LinkedIn 限号。

---

## 5. 投之前，像人一样还要看什么（不只看 JD）

系统帮你读 JD 内容并打分，但**按下提交前**，你（或后续我们做的增强）还要看这些：

- **公司近况**：融资/裁员/重组？Glassdoor 评价与文化？（可加 Tavily/新闻做"公司调研"节点）
- **薪资 vs 期望**：对得上你 $195k–270k 的档吗？别虚高也别屈就。
- **seniority 真匹配**：写 Director 但实际是个人贡献者？看汇报线和团队规模。
- **岗位新鲜度**：常年挂着/反复重发 = 可能是"幽灵岗"，别浪费时间。
- **远程/坐班是否属实**、**是否需要 sponsorship**、**是否与竞业冲突**。
- **JD 红旗**：描述含糊、"什么都要"、"rockstar/wear many hats" 往往是坑。
- **内推路径**：有没有能帮你递简历的人？

> 这些里"公司调研""薪资区间""幽灵岗识别"我可以逐步做成自动信号加进打分——你要的话我接着做。

---

## 6. 你要的"几个 agent"——现状与建议

| Agent | 你的设想 | 现状 |
|---|---|---|
| 每日找 job + 内容匹配 | ✅ | 已做（多平台 + LLM 语义打分 + 三方向分发） |
| 改简历 agent | ✅ | 已做（`tailor.py` 的 ATS 对齐，如实改写 bullet） |
| 改 cover letter agent | ✅ | 已做（自然、真诚、不 AI 味） |
| 自动投递 | ⚠️ | **不建议全自动**；用"系统起草 + Simplify 半自动提交"保质量 |

**市面现成工具搭配建议**：发现+匹配+起草用**本系统**（最懂你的内容匹配）；填表提交用 **Simplify**（免费、你掌控）；
ATS 体检可选 **Jobscan**；投递追踪可选 **Teal / Huntr**。

---

## 7. 30 天冲刺清单

- [ ] 加齐 GitHub Secrets（`RAPIDAPI_KEY`、`OPENAI_API_KEY`、`SMTP_*`、`EMAIL_TO`），Actions 手动跑一次验证三封邮件
- [ ] 按第 3 节改写 LinkedIn Headline / About（关键词化）+ 打开 Open to work
- [ ] 报名/推进 **AIGP** 考试
- [ ] 每周按第 4 节节奏：精修 5–8 个申请 + 2–3 个内推
- [ ] 装 **Simplify** 浏览器插件
- [ ] （可选）让我加"公司调研 + 幽灵岗识别"打分信号

---

*说明：本方案中的市场/薪资数据来自公开来源（GRC Careers / ai-governance-jobs.com、IAPP 2025–26 Salary & Jobs Report、ISACA），仅供参考；具体以实际 JD 与谈判为准。方案只基于你简历真实信息，不夸大。*
