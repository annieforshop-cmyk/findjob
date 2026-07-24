# 目标公司策略 —— 根据你的简历量身推导

> 你的牌：CPA + 10 年金融内审（MS Director / BNY VP）+ 2 年企业级 AI 治理实操
> （框架、委员会、模型风险协作、EU AI Act / NIST AI RMF / ISO 42001）+ 对 200+ 高管布道 AI。
> 这个组合的稀缺点：**既懂控制/监管语言，又真的动手管过 AI**。市场上两边都懂的人极少。
> 下面五类公司就是按"谁最缺这副牌"排的。

## Tier 1 · 受监管金融机构的 AI 治理/AI 风险岗（主战场，≥50% 精力）

**谁**：银行（BMO、Citi、Capital One、GS）、保险（MetLife、Allstate、GEICO、Travelers）、
资管/财富（LPL、Invesco、BlackRock、Schwab）、GSE 与市场基础设施（Fannie/Freddie、DTCC、Nasdaq、Moody's、FINRA）。

**为什么是你**：这些机构 2025-26 被监管倒逼建 AI 治理职能，招的就是"内审/风险出身 + 懂 AI"
——你的简历就是这个 JD 的答案。职级带宽（Sr Mgr–VP/Director）和薪资带宽（$150k–280k）都对口。
**怎么打**：三条线同时投——二线 AI 风险治理（最对口）、一线 AI 治理框架、内审部的 AI 审计专线。

## Tier 2 · GRC/审计/合规软件商（你的知识就是他们的产品，~15%）

**谁**：AuditBoard、Workiva、OneTrust、Diligent、LogicGate、Vanta、Drata、Credo.AI、Holistic AI。

**为什么是你**：这些公司卖的就是"审计/合规/AI 治理工作流"。你 10 年审计 = 产品的活体需求库。
岗位形态：Solutions/Advisory、产品领域专家、客户侧 AI 治理顾问、内部合规负责人。
**加分项**：多数 remote-first（符合你的 remote 偏好）；成长期股权上行空间；不看你没有的工程背景。

## Tier 3 · AI 实验室与 AI scale-up 的治理/合规/保证职能（~10%）

**谁**：Anthropic、OpenAI、Scale、Mistral、xAI、Cohere，以及应用层（Harvey、Sierra、Writer、Glean）。

**为什么是你**：前沿 AI 公司开始要向企业客户和监管证明自己可信——需要能建 compliance/assurance
program 的人。你的审计方法论 + AIGP + 真实治理框架经验是硬通货。竞争激烈但一旦命中，
职业路径直通"Head of AI Assurance"。每家通常只有 1-2 个这类岗，看到就投，不等。

## Tier 4 · 咨询/Big-4 的 AI 治理线 + 猎头渠道（~15%）

**谁**：PwC/EY/KPMG/Deloitte 的 Responsible AI / AI Risk 线、RSM、Crowe、Grant Thornton、
Guidehouse、FTI、CFGI；猎头 Selby Jennings、Robert Half、Michael Page（模型风险/内审单子多）。

**为什么是你**：CPA + Big4 转包履历（KPMG/COSO 测试）是他们的标准入场券，AI 治理交付经验直接卖钱。
猎头单子就算单岗不成，你的简历会进他们的库——被动机会源源不断。**每周固定 2-3 个猎头触达**。

## Tier 5 · 欧洲公司与 EU AI Act 红利（机会型，~10%）

**谁**：Revolut、Wise、Adyen、Klarna、N26、Checkout.com（都有美国实体），以及任何在美上市/
展业、需要应对 EU AI Act 的欧企。

**为什么是你**：EU AI Act 2026-27 全面生效，你是少数系统跟过它的美国审计背景候选人。
**规则**：只投 remote-US 或美国实体的岗；纯欧洲 onsite（需要当地工签）不投——管道已按此打分。

## 工作模式与公司规模的打分规则（已写进管道）

- **Remote +2 / Hybrid −2 / Onsite −4**：同分岗位 remote 永远排前面。
- 小公司/startup 不再被品牌权重埋没：行业分只占 10%，语义匹配（简历↔JD 内容）占大头。
- 欧洲岗：能 remote-US / 有美国实体 → 正常打分；仅限欧洲本地 → location_ok=false 直接过滤。

## 渠道矩阵（每天自动跑）

| 渠道 | 覆盖 | 引擎 |
|---|---|---|
| 公司官网直连（~140 板） | Tier 1/2/3/5 的官网新岗 | ats_boards（无需 key） |
| LinkedIn/Indeed/Glassdoor/ZipRecruiter | 全市场含猎头代招 | JSearch（需 RAPIDAPI_KEY） |
| Adzuna 聚合 | 长尾/中小公司 | Adzuna（需 key） |
| Dream 50 精评 | 最想去公司的逐岗深评 | dream.py |

每天总扫描量 2000+ → 语义预筛(embedding) → GPT 十维深评 80 个/方向 → 邮件 Top 50（每公司≤3、
已投自动隐藏）。投完记一条 `python -m src.track apply "公司" "职位"`，它就从此消失并进入跟进提醒。
