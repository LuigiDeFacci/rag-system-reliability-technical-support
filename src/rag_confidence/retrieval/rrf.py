"""Reciprocal Rank Fusion over aligned chunk rankings.

RRF combines ordinal evidence without adding BM25 and cosine scores, whose
scales are not directly comparable across questions.
"""

from __future__ import annotations

from rag_confidence.retrieval.semantic import RankedAggregatedDocument, RankedChunk


def reciprocal_rank_fusion(
    lexical: list[RankedChunk],
    semantic: list[RankedChunk],
    *,
    rrf_k: int = 60,
) -> tuple[list[RankedChunk], list[RankedAggregatedDocument]]:
    if rrf_k <= 0:
        raise ValueError("rrf_k must be positive")
    lexical_by_id = {item.chunk_id: item for item in lexical}
    semantic_by_id = {item.chunk_id: item for item in semantic}
    if set(lexical_by_id) != set(semantic_by_id):
        raise ValueError("RRF inputs must rank the same chunk IDs")
    lexical_rank = {item.chunk_id: rank for rank, item in enumerate(lexical, start=1)}
    semantic_rank = {item.chunk_id: rank for rank, item in enumerate(semantic, start=1)}
    fused = []
    for chunk_id, item in lexical_by_id.items():
        score = 1.0 / (rrf_k + lexical_rank[chunk_id]) + 1.0 / (rrf_k + semantic_rank[chunk_id])
        fused.append(
            RankedChunk(
                row_index=item.row_index,
                chunk_id=chunk_id,
                document_id=item.document_id,
                chunk_index=item.chunk_index,
                body_start_char=item.body_start_char,
                body_end_char=item.body_end_char,
                score=score,
            )
        )
    fused.sort(
        key=lambda item: (
            -item.score,
            lexical_rank[item.chunk_id],
            semantic_rank[item.chunk_id],
            item.chunk_id,
        )
    )
    best_by_document: dict[str, RankedChunk] = {}
    for item in fused:
        best_by_document.setdefault(item.document_id, item)
    documents = [
        RankedAggregatedDocument(document_id, item.score, item.chunk_id)
        for document_id, item in best_by_document.items()
    ]
    return fused, documents
