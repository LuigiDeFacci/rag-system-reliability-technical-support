"""Evaluate chunk-context sufficiency and its document-level proxy."""

from __future__ import annotations

from typing import Any

import pandas as pd

from rag_confidence.evaluation.retrieval_metrics import aggregate_retrieval_metrics
from rag_confidence.retrieval.semantic import interval_union_covers


def evaluate_context_rankings(
    questions: pd.DataFrame,
    rankings: pd.DataFrame,
    cutoffs: list[int],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Evaluate safe ranking artifacts against gold fields kept in questions."""
    if rankings["query_id"].duplicated().any():
        raise ValueError("Rankings must contain exactly one row per query_id")
    ranking_by_query = rankings.set_index("query_id")
    if set(questions["query_id"]) != set(ranking_by_query.index):
        raise ValueError("Question and ranking query IDs differ")

    records = []
    for row in questions.itertuples(index=False):
        ranking = ranking_by_query.loc[str(row.query_id)]
        chunk_documents = [str(value) for value in ranking["ranked_chunk_document_ids"]]
        chunk_starts = [int(value) for value in ranking["ranked_chunk_body_starts"]]
        chunk_ends = [int(value) for value in ranking["ranked_chunk_body_ends"]]
        document_ids = [str(value) for value in ranking["ranked_document_ids"]]
        answerable = bool(row.answerable)
        gold_document_id = str(row.gold_document_id) if answerable else None
        answer_start = int(row.answer_start) if answerable else None
        answer_end = int(row.answer_end) if answerable else None
        document_rank = document_ids.index(gold_document_id) + 1 if answerable else None
        containing_chunk_rank = None
        if answerable:
            containing_chunk_rank = next(
                (
                    rank
                    for rank, (document_id, start, end) in enumerate(
                        zip(chunk_documents, chunk_starts, chunk_ends, strict=True), start=1
                    )
                    if document_id == gold_document_id
                    and start <= answer_start
                    and answer_end <= end
                ),
                None,
            )
        evaluation = {
            "query_id": str(row.query_id),
            "research_split": str(row.research_split),
            "answerable": answerable,
            "gold_document_id": gold_document_id,
            "gold_document_rank": document_rank,
            "first_containing_chunk_rank": containing_chunk_rank,
        }
        for cutoff in cutoffs:
            intervals = [
                (start, end)
                for document_id, start, end in zip(
                    chunk_documents[:cutoff],
                    chunk_starts[:cutoff],
                    chunk_ends[:cutoff],
                    strict=True,
                )
                if answerable and document_id == gold_document_id
            ]
            evaluation[f"evidence_at_{cutoff}"] = bool(
                answerable and interval_union_covers(intervals, answer_start, answer_end)
            )
            evaluation[f"gold_document_at_{cutoff}"] = bool(
                document_rank is not None and document_rank <= cutoff
            )
        records.append(evaluation)

    evaluations = pd.DataFrame(records)
    metrics: dict[str, Any] = {}
    for split, split_frame in evaluations.groupby("research_split", sort=False):
        answerable_frame = split_frame[split_frame["answerable"]]
        containing_ranks = [
            None if pd.isna(value) else int(value)
            for value in answerable_frame["first_containing_chunk_rank"]
        ]
        document_ranks = [int(value) for value in answerable_frame["gold_document_rank"]]
        split_metrics: dict[str, Any] = {
            "all_queries": int(len(split_frame)),
            "containing_chunk": aggregate_retrieval_metrics(containing_ranks, cutoffs),
            "document_proxy": aggregate_retrieval_metrics(document_ranks, cutoffs),
        }
        for cutoff in cutoffs:
            split_metrics[f"context_evidence_positive_rate_at_{cutoff}"] = float(
                split_frame[f"evidence_at_{cutoff}"].mean()
            )
            split_metrics[f"answerable_context_recall_at_{cutoff}"] = float(
                answerable_frame[f"evidence_at_{cutoff}"].mean()
            )
        metrics[str(split)] = split_metrics
    return evaluations, metrics
