# Career OS — 完整使用手册

> 核心原则：**Job Search ≠ Apply More**。
> Job Search = 精准匹配 + Recruiter + Networking + Personal Brand + ATS 优化 + Career Strategy。
> 这套系统把上面每一项都自动化/半自动化，把你每天的求职时间压到 **20-30 分钟**。

---

## 每天的样子

早上收到 **一封 Career Brief 邮件**（不再是三封），包含：

| 区块 | 来源 | 你要做的 |
|---|---|---|
| ⭐ Dream Company 官网新岗 | 直连 Target-50 公司 ATS API（不靠 LinkedIn） | 优先投，找内推 |
| 🎯 Top Jobs | 三个方向合并，按**综合 Fit Score** 排序 | 投 1-3 个最高分 |
| 🔎 公司尽调 | Google News + LLM（裁员风险/AI 布局/CL 切入点） | 复制切入点进 cover letter |
| 🤝 内推人选 | 校友/前同事/决策者的 LinkedIn 精准搜索链接 | 每岗发 1-2 条连接请求 |
| ⏰ 跟进提醒 | 你的申请记录（7 天/14 天规则） | 发 follow-up 消息 |
| 📇 Recruiter Pipeline | recruiters.yaml 到期提醒 + 周一新增计划 | 维持每周 5-10 个新连接 |
| ✍️ LinkedIn 内容 | 周一自动生成本周帖子草稿 | 编辑 20% 后发布 |

---

## 十大模块对照表

### 1. Recruiter Pipeline（`career/recruiters.yaml` + `src/network.py`）
- 周一 Brief 给出本周新增计划（轮换目标猎头公司 + 一键 LinkedIn 搜索链接 + 破冰消息草稿）。
- 已有关系超过 30 天未联系自动提醒。
- 记录：`python -m src.track recruiter "Jane Doe" --firm "Selby Jennings"`；联系过就 `python -m src.track touch "Jane"`。

### 2. Dream Companies（`career/dream_companies.yaml` + `src/dream.py`）
- Target-50 名单（银行/资管/保险/咨询/AI 公司），双通道监控：
  - **通道1**：Greenhouse/Lever/Ashby/SmartRecruiters/Workday 公开 API 每日直拉官网岗位；
  - **通道2**：聚合源(JSearch/Adzuna)结果里命中 Target-50 公司名的岗位自动打 ⭐ 并置顶。
- 手动看全量：`python -m src.dream --all`。改名单/加公司直接编辑 yaml。

### 3. Company Research Agent（`src/research.py`）
- 每天自动尽调 Brief 里最强的几家公司：近期新闻、AI 布局、裁员风险、融资/财务、
  该找的人（title）、Glassdoor/Blind 主题（标注"需验证"）、**cover letter 切入点**、**面试角度**。
- 缓存 14 天不重复花钱。手动：`python -m src.research "Citi" --title "AI Governance Director"`。
- Cover letter 生成和面试 prep 会自动引用。

### 4. Resume Story Library（`career/stories/` + `src/stories.py`）
- 8 个 STAR 故事已按你简历预填（AI 治理框架、持续监控、高管演讲、Issue Validation、
  Dashboard、企业风险评估等），`[方括号]` 处补上真实数字即可。
- Resume bullet、Cover Letter（`src.tailor` 自动注入）、面试（`src.interview prep` 自动注入）全部复用。

### 5. Interview Knowledge Base（`career/interviews/` + `src/interview.py`）
- 面试后 60 秒记录：`python -m src.interview log --company Citi --stage "HM round" --questions "Q1|Q2" --notes "..."`。
- 面试前生成准备包（历史被问过的题⭐ + 匹配 STAR 故事 + 公司尽调 + 预测 10 题 + 反问 5 题）：
  `python -m src.interview prep --company Citi --profile ai-governance`。

### 6. Personal Branding（`src/branding.py`）
- 每周一 Brief 附一篇 LinkedIn 帖子草稿：10 个话题轮换（NIST AI RMF 落地、EU AI Act、
  审 GenAI 清单、Agentic AI 审计……），基于你真实经历、practitioner 口吻、不 AI 味。
- 手动生成/换话题：`python -m src.branding --topic "..."`。

### 7. Fit Score v2（`src/ai_score.py` + `config.yaml: fit_weights`）
- 不止 ATS 关键词：每个岗位 12 个维度打分——技能/职级/年限/行业/领导力/AI治理相关度/
  成长/薪资/**职业路径**/**Recruiter 回复概率**/裁员风险/幽灵岗。
- 加权合成综合分排序，权重在 `config.yaml` 可调（默认职业路径 12%、回复概率 8%）。

### 8. Networking Agent（`career/network.yaml` + `src/network.py`）
- 每个 Top 岗位自动生成：Clark/上大校友@该公司、前 BNY/KPMG 同事@该公司、
  CAE/Head of AI Governance 等决策者、内部 recruiter 的 LinkedIn 精准搜索链接 + 破冰草稿。
- `python -m src.network --company "Goldman Sachs" --title "..."` 单独生成。

### 9. Career Strategy（`config.yaml: career_goal`）
- 3-5 年目标（Head/Director of AI Governance）写进配置，AI 对每个岗位单独评
  `career_path_fit`（垫脚石价值/品牌/scope 轨迹），并占综合分 12% 权重——
  避免被"薪资高但偏离方向"的岗位带偏。

### 10. Dashboard / Career Brief（`src/brief.py`）
- 以上一切合成每天一封邮件。GitHub Actions 每天 UTC 13:00 自动跑。
- 手动：`python -m src.brief --dry-run`（本地预览）。

---

## 命令速查

```bash
python -m src.brief --dry-run                 # 预览今日 Career Brief
python -m src.dream --all                     # 看 Dream 公司全部在招匹配岗
python -m src.research "Citi"                 # 尽调一家公司
python -m src.network --company "Citi"        # 该公司的内推人选 + 破冰消息
python -m src.network --recruiters            # recruiter pipeline 状态 + 周计划
python -m src.track apply "Citi" "Director, AI Governance" --url ... --via referral
python -m src.track status "Citi" interviewing
python -m src.track recruiter "Jane Doe" --firm "Selby Jennings"
python -m src.track touch "Jane Doe"          # 记录今天联系过
python -m src.interview log --company Citi --questions "Q1|Q2"
python -m src.interview prep --company Citi   # 面试准备包
python -m src.branding                        # 本周 LinkedIn 帖草稿
python -m src.tailor --profile ai-governance 3  # 某岗位 ATS 对齐 + cover letter
```

## 需要你人肉做的（系统做不了，但已帮你把成本降到最低）
1. **点发送**：连接请求、follow-up、申请提交——系统写好草稿，你过目后发。
2. **补故事数字**：`career/stories/` 里的 `[方括号]` 填上真实数据（一次性 30 分钟）。
3. **记录**：投了/面了/联系了 → 一行命令记下来，系统才能替你记住和提醒。
4. **发 LinkedIn 帖**：每周一 5 分钟，编辑草稿后发布。

## 维护
- Dream 公司 ATS token 失效时每日 Actions 日志会提示 `dream: X failed`，改 yaml 即可。
- 所有状态（去重/研究缓存/发帖历史）在 `data/`，由 CI 自动回写提交。
- `career/` 全部是你的资产文件——换任何求职工具都带得走。
