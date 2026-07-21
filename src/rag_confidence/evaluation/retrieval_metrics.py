"""Metrics for binary-relevance document retrieval."""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any


def aggregate_retrieval_metrics(
    gold_ranks: Iterable[int | None], ks: Iterable[int]
) -> dict[str, Any]:
    ranks = list(gold_ranks)
    if not ranks:
        raise ValueError("At least one answerable query is required")
    cutoffs = sorted(set(int(k) for k in ks))
    if not cutoffs or cutoffs[0] <= 0:
        raise ValueError("All k values must be positive")
    metrics: dict[str, Any] = {
        "answerable_queries": len(ranks),
        "mrr": sum(0.0 if rank is None else 1.0 / rank for rank in ranks) / len(ranks),
    }
    for cutoff in cutoffs:
        metrics[f"recall_at_{cutoff}"] = sum(
            rank is not None and rank <= cutoff for rank in ranks
        ) / len(ranks)
        metrics[f"ndcg_at_{cutoff}"] = sum(
            0.0 if rank is None or rank > cutoff else 1.0 / math.log2(rank + 1.0) for rank in ranks
        ) / len(ranks)
    return metrics
