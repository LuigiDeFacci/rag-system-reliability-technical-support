"""Exact semantic ranking helpers for the candidate-set experiment."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RankedChunk:
    row_index: int
    chunk_id: str
    document_id: str
    chunk_index: int
    body_start_char: int
    body_end_char: int
    score: float


@dataclass(frozen=True)
class RankedAggregatedDocument:
    document_id: str
    score: float
    best_chunk_id: str


def rank_candidate_chunks(
    query_embedding: np.ndarray,
    chunk_embeddings: np.ndarray,
    chunk_records: list[dict[str, object]],
    rows_by_document: dict[str, list[int]],
    candidate_document_ids: list[str],
) -> tuple[list[RankedChunk], list[RankedAggregatedDocument]]:
    """Rank candidate chunks exactly, then aggregate documents by maximum chunk score."""
    candidate_position = {
        document_id: position for position, document_id in enumerate(candidate_document_ids)
    }
    row_indices = [
        row_index
        for document_id in candidate_document_ids
        for row_index in rows_by_document[document_id]
    ]
    scores = chunk_embeddings[row_indices] @ query_embedding
    ranked = []
    for row_index, score in zip(row_indices, scores, strict=True):
        record = chunk_records[row_index]
        ranked.append(
            RankedChunk(
                row_index=row_index,
                chunk_id=str(record["chunk_id"]),
                document_id=str(record["document_id"]),
                chunk_index=int(record["chunk_index"]),
                body_start_char=int(record["body_start_char"]),
                body_end_char=int(record["body_end_char"]),
                score=float(score),
            )
        )
    ranked.sort(
        key=lambda item: (
            -item.score,
            candidate_position[item.document_id],
            item.chunk_index,
            item.chunk_id,
        )
    )

    best_by_document: dict[str, RankedChunk] = {}
    for item in ranked:
        best_by_document.setdefault(item.document_id, item)
    ranked_documents = [
        RankedAggregatedDocument(document_id, item.score, item.chunk_id)
        for document_id, item in best_by_document.items()
    ]
    return ranked, ranked_documents


def interval_union_covers(
    intervals: list[tuple[int, int]], target_start: int, target_end: int
) -> bool:
    """Return whether the union of intervals continuously covers the target span."""
    if target_start < 0 or target_end <= target_start:
        return False
    clipped = sorted(
        (max(start, target_start), min(end, target_end))
        for start, end in intervals
        if start < target_end and target_start < end
    )
    covered_until = target_start
    for start, end in clipped:
        if start > covered_until:
            return False
        covered_until = max(covered_until, end)
        if covered_until >= target_end:
            return True
    return False
