# Recruiter Magnet — 让猎头主动找到你的完整打法

> 你的实际数据已经证明：**猎头带来的面试 >> 海投**。
> 猎头找人只有一个入口：**LinkedIn Recruiter 的关键词搜索** + 自家候选人数据库。
> 所以策略只有两条：① 让你在搜索结果里排前面；② 进入尽可能多的猎头数据库。
> 下面按投入产出比排序，⏱ 是一次性投入时间。

---

## 第一部分：Inbound——让猎头搜到你（一次性 ~90 分钟，长期复利）

### 1. LinkedIn Headline 重写（⏱ 10 分钟，杠杆最高的一条）
猎头搜的是**关键词**，不是读你的故事。Headline 是搜索权重最高的字段。
不要只写 `Director at XXX`，用这个公式（岗位词 + 技能词 + 证书）：

```
AI Governance & Internal Audit Director | AI Risk · Model Risk · NIST AI RMF · EU AI Act | CPA | Ex-Big4/BNY
```

覆盖了猎头会搜的所有变体：AI Governance / Internal Audit / Director / AI Risk / Model Risk / CPA。

### 2. Open to Work——只对猎头可见（⏱ 5 分钟）
LinkedIn 头像下 → Open to → Finding a new job → **"Recruiters only"**（同事看不到）。
Job titles 填满 5 个搜索变体（这直接决定你出现在哪些搜索里）：
- Director, AI Governance
- Head of AI Governance
- AI Risk Director
- Internal Audit Director
- Senior Manager, AI Governance

Location: 勾 Remote + New York + 你能接受的城市。Start date: "Actively looking"（猎头端有加权）。

### 3. About + Skills 关键词填充（⏱ 30 分钟）
- **About 前两行**（搜索抓取重点）：把你真实技能词全部自然写进去：
  AI governance, responsible AI, NIST AI RMF, EU AI Act, ISO/IEC 42001, AI risk
  assessment, model risk, internal audit, enterprise risk, continuous monitoring,
  CPA, AIGP。
- **Skills 区**：加满 50 个（LinkedIn 上限），把 "Artificial Intelligence Governance"
  "Internal Auditing" "Risk Management" 置顶前三（前三权重最高）。
- **每段工作经历**里也要出现这些词（经历字段同样参与搜索）。

### 4. 进入猎头数据库（⏱ 45 分钟，一次注册长期躺收）
按优先级注册并上传简历（用 `profiles/ai-governance/resume.md` 的内容）：

| 平台 | 为什么 |
|---|---|
| **eFinancialCareers** | 金融业猎头的主力候选人库，你的画像是他们的核心客户 |
| **Ladders** ($100k+) | 猎头/企业按薪资带搜人 |
| **Indeed 简历公开** | 大量代招猎头在 Indeed 数据库搜人 |
| **BlueSteps** (AESC) | 高管猎头协会官方数据库，Korn Ferry/Heidrick 级别的 retained search 用它 |
| **ExecThread** | 隐藏高管岗互换社区 |
| 猎头公司官网 talent network | Selby Jennings、Michael Page、Robert Half、Korn Ferry 官网都有 "Submit your resume / Join talent network"——逐家提交一次 |

### 5. 每周一篇 LinkedIn 内容（已自动化 ✅）
系统每周一生成帖子草稿（`src/branding.py`）。这不只是"个人品牌"——
**发帖会让你出现在搜索之外的第二个入口**：猎头刷 feed、看谁在聊 AI governance。
发帖 → 被看到 → 主页访问 → InMail。坚持 8-12 周会有明显的 inbound 增量。

---

## 第二部分：Outbound——系统性出现在猎头面前（已自动化 ✅）

### 每日 Brief 里的 🎯 猎头代招岗（新功能）
聚合源抓到的岗位里，凡是猎头公司发的（Selby Jennings、Michael Page、Robert Half
等 40+ 家已内置识别），自动打 🎯 标。**这类岗位要优先投**：
- 投递 = 你的简历进入该猎头的数据库（以后所有类似岗位他都会想起你）
- 投完 60 秒动作：LinkedIn 搜该岗位的发帖 recruiter → 发连接请求（Brief 有草稿）

### 每周一的 Recruiter 连接计划（已自动化 ✅）
Brief 周一给出 3-4 家目标猎头公司的精准搜索链接 + 破冰消息，每周新增 5-10 个连接。
坚持 4 周 = 30+ 个金融风控/审计线猎头认识你。

### 关系复利（记录进 pipeline，系统自动提醒）
每次猎头联系你——**无论岗位合不合适**——做三件事：
1. `python -m src.track recruiter "名字" --firm "公司"` 记进 pipeline（30 天后自动提醒跟进）
2. 回复模板：*"这个岗位不太匹配，但我在积极看 AI Governance / IA Director 方向。
   你或你同事手上有相关的 search 吗？我可以发一份针对性简历。"*
   ——一个猎头背后是一个团队，**要求转介绍**是最被低估的动作
3. 岗位不合适也认真回：猎头库里标注"responsive"的候选人会被优先想起

---

## 为什么不做"自动发消息"
LinkedIn 自动化群发工具（auto-connect/auto-DM）违反服务条款，封号率很高，
而你的 LinkedIn 恰恰是猎头 inbound 的唯一入口——不值得赌。
本系统的边界：**找人、写稿、排程、提醒全自动化，点发送的那一下是你**。
每天实际操作量：3-5 次点击。

---

## 执行节奏（结合每日 Brief）
- **今天**：第 1-2 项（Headline + Open to Work，15 分钟）——当天就会进入搜索结果
- **本周内**：第 3-4 项（About/Skills + 数据库注册）
- **每天**：Brief 里的 🎯 岗位优先投 + 连接发帖 recruiter
- **每周一**：发 LinkedIn 帖 + 完成 recruiter 新增计划
- **每次猎头来找你**：记 pipeline + 要转介绍
