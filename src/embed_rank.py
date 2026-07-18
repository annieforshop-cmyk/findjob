"""语义预筛（Stage-1.5）：按"意思相近"排序，而不是死关键词。

关键词筛（score.py）会漏掉措辞不同但意思一样的岗位（比如 JD 写
"AI oversight framework" 而简历写 "AI governance framework"）。
这一层把整份简历和每个 JD 用 embedding 变成向量，按余弦相似度衡量
语义重合度，与关键词分混合后重排——语义权重默认更高。

排序后的前 max_candidates 个进入 Stage-2 的 GPT 深度打分。
成本：text-embedding-3-small 约 $0.02/百万 token，每天几千个 JD 也只有几美分。
没有 OPENAI_API_KEY 时自动跳过，退回关键词排序。
"""
from __future__ import annotations

import math
import os
import sys

from .sources.base import Job

BATCH = 96          # embeddings API 单次批量
JD_CHARS = 1600     # 每个 JD 取前 N 字符（标题+公司+正文开头信息量最大）


def _client():
    try:
        from openai import OpenAI
    except ImportError:
        return None
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    return OpenAI()


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


def rank(jobs: list[Job], resume: str, cfg: dict) -> tuple[list[Job], bool]:
    """按 (1-w)*关键词分 + w*语义相似度 重排。Returns (jobs, used_embeddings)."""
    ecfg = cfg.get("embed_rank", {}) or {}
    if not ecfg.get("enabled", True) or not resume.strip() or not jobs:
        return jobs, False
    client = _client()
    if client is None:
        print("  embed_rank: no OPENAI_API_KEY/openai — keyword order kept", file=sys.stderr)
        return jobs, False

    model = ecfg.get("model", "text-embedding-3-small")
    cap = int(ecfg.get("max_jobs", 600))
    w = float(ecfg.get("semantic_weight", 0.6))
    pool = jobs[:cap]

    try:
        rvec = client.embeddings.create(model=model, input=[resume[:6000]]).data[0].embedding
    except Exception as e:
        print(f"  embed_rank: resume embedding failed: {e}", file=sys.stderr)
        return jobs, False

    texts = [f"{j.title} | {j.company}\n{(j.description or j.location or '')[:JD_CHARS]}"
             for j in pool]
    vecs: list[list[float] | None] = []
    for i in range(0, len(texts), BATCH):
        chunk = texts[i:i + BATCH]
        try:
            resp = client.embeddings.create(model=model, input=chunk)
            vecs.extend([d.embedding for d in resp.data])
        except Exception as e:
            print(f"  embed_rank: batch {i // BATCH} failed: {e}", file=sys.stderr)
            vecs.extend([None] * len(chunk))

    sims = []
    for j, v in zip(pool, vecs):
        if v is not None:
            j.embed_sim = round(_cos(rvec, v) * 100, 1)
            sims.append(j.embed_sim)
    if not sims:
        return jobs, False

    # 余弦相似度的绝对值区间窄（大致 10-70），min-max 归一到 0-100 再混合
    lo, hi = min(sims), max(sims)
    span = (hi - lo) or 1.0
    blended: dict[str, float] = {}
    for j in pool:
        s_norm = (j.embed_sim - lo) / span * 100 if j.embed_sim >= 0 else 0.0
        blended[j.id] = (1 - w) * min(j.score, 100) + w * s_norm
    pool.sort(key=lambda j: -blended[j.id])
    print(f"  embed_rank: semantically ranked {len(sims)}/{len(pool)} jobs "
          f"(weight {w:.0%} semantic)", file=sys.stderr)
    return pool + jobs[cap:], True
