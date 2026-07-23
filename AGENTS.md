# Agent Instructions — findjob 投递工作流 SOP

给任何在这个仓库里工作的 AI agent（Claude Code / Codex / 其他）。
本文件把每日邮件（发现岗位）和"实际投递"衔接起来：用户从「每日新岗」
邮件里挑出岗位后，agent 按这里的 SOP 协助完成申请。工作流设计参考了
开源项目 ApplyPilot 的安全边界与状态模型。

## 事实来源（按优先级）

1. `career/candidate_profile.yaml` — 申请表事实的唯一来源；`TBD` = 未知
2. `profiles/<方向>/resume.md` — 简历（技能/经历的事实来源）
3. `career/answer_bank.md` — 申请表常见问题的可复用措辞
4. `career/stories/` — STAR 故事库（cover letter / 面试素材）
5. `config.yaml` `candidate:` — 画像摘要

## 硬性安全边界（不可协商）

- **绝不编造**：经历、学历、日期、雇主、签证状态、薪资、作品、推荐人。
  简历里没有的就是没有。
- **高影响事实缺失 → 停下来问**（Needs-user）：candidate_profile 里标 TBD
  的字段、自愿披露题、背调、竞业、超出区间的薪资问题。
- **最终提交前必须停**：展示"公司/岗位/所用简历/关键答案"摘要，等用户
  确认后才点 Submit。自动化到提交前一步为止。
- **遇到即移交**：CAPTCHA / Cloudflare / 登录 / 2FA / 付款 / 权限弹窗。
  不绕过任何站点风控。
- **只算确认成功**：看到 "Application submitted / Thank you" 页面或明确
  状态才算投出；点了按钮没见确认页 → 记 Pending confirmation。

## 每个岗位必须落在一个状态

`Submitted` / `Pending`（值得投、待处理）/ `Skipped`（写明原因）/
`Blocked`（自动化无法继续，写明卡点）/ `Needs-user`（缺高影响事实）。

记录方式（已有 CLI）：

```bash
python -m src.track apply "公司" "岗位" --url ... --via referral   # 投出后记录
python -m src.track status "公司" interviewing                     # 状态推进
python -m src.track list                                           # 查看全部
```

Skipped/Blocked/Needs-user 记在 `career/applications.yaml` 的 notes 或
直接回复用户说明，不需要为未投递的岗位建正式记录。

## 两种投递模式（借鉴 ApplyPilot 海投/精投）

- **Volume（海投）**：直接用 `profiles/<方向>/resume.md` 对应的现成简历，
  快速走完申请表。适合批量、低摩擦岗（无需新建账号、无视频/长文书）。
- **Precision（精投）**：高匹配岗先跑
  `python -m src.tailor --profile <方向> "<岗位链接或JD>"`
  生成 ATS 关键词对齐 + cover letter 草稿（自动注入 STAR 故事），
  用户确认方向后再填表。

判断标准：邮件里综合分 ≥75 → 建议 Precision；60–75 → Volume。

## 重复卡点 → 沉淀成规则

同一个 ATS/字段反复出问题（下拉框假选中、地址匹配、简历上传静默失败），
把教训写进本文件末尾的 Lessons 段，越用越顺。

## Lessons（持续追加）

- （暂无：第一次遇到可复现卡点时在这里记录 ATS 名 + 字段 + 解法）
