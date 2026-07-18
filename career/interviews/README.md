# Interview Knowledge Base — 每次面试都让下一次更强

每家公司一个文件（如 `citi.md`）。记录每一轮：面试官、问题、你的回答要点、
反馈、下次改进。`src.interview` 会在你准备同一家公司（或同类岗位）时自动带出历史。

## 用法
```bash
# 面试后 60 秒内快速记录（趁记忆新鲜）
python -m src.interview log --company Citi --stage "HM round" \
  --interviewer "Jane D (Audit MD)" \
  --questions "如何审计 GenAI 用例|讲一个 issue validation 顶回去的例子" \
  --notes "对 NIST AI RMF 很感兴趣；答 dashboard 那题不够量化"

# 面试前生成准备包（历史题 + 匹配的 STAR 故事 + 公司研究）
python -m src.interview prep --profile ai-governance --company Citi 3
```

## 模板（手动建文件也行）
见 `_template.md`。
