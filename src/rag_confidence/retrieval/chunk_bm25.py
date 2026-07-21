"""Memory-conscious BM25 scoring for the shared chunk corpus."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Sequence

import numpy as np

from rag_confidence.retrieval.bm25 import technical_tokenize
from rag_confidence.retrieval.semantic import RankedAggregatedDocument, RankedChunk


class ChunkBM25Statistics:
    """Global chunk statistics without retaining a token Counter for every chunk."""

    def __init__(
        self,
        texts: Iterable[str],
        *,
        k1: float = 1.2,
        b: float = 0.75,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be positive")
        if not 0 <= b <= 1:
            raise ValueError("b must be between zero and one")
        self.k1 = float(k1)
        self.b = float(b)
        document_frequency: Counter[str] = Counter()
        lengths = []
        for text in texts:
            tokens = technical_tokenize(text)
            lengths.append(len(tokens))
            document_frequency.update(set(tokens))
        if not lengths:
            raise ValueError("At least one chunk is required")
        self.lengths = np.asarray(lengths, dtype=np.int32)
        self.chunk_count = len(lengths)
        self.average_length = float(self.lengths.mean())
        self.idf = {
            term: math.log(1.0 + (self.chunk_count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def score(self, query_tokens: Sequence[str], text: str, row_index: int) -> float:
        counts = Counter(technical_tokenize(text))
        length_normalization = (
            1.0 - self.b + self.b * (int(self.lengths[row_index]) / self.average_length)
        )
        score = 0.0
        for term, query_frequency in Counter(query_tokens).items():
            term_frequency = counts.get(term, 0)
            if not term_frequency:
                continue
            numerator = term_frequency * (self.k1 + 1.0)
            denominator = term_frequency + self.k1 * length_normalization
            score += query_frequency * self.idf.get(term, 0.0) * numerator / denominator
        return score


def rank_bm25_candidate_chunks(
    query: str,
    passage_texts: Sequence[str],
    chunk_records: list[dict[str, object]],
    rows_by_document: dict[str, list[int]],
    candidate_document_ids: list[str],
    statistics: ChunkBM25Statistics,
) -> tuple[list[RankedChunk], list[RankedAggregatedDocument]]:
    """Rank all chunks from candidate documents and aggregate documents by maximum."""
    candidate_position = {
        document_id: position for position, document_id in enumerate(candidate_document_ids)
    }
    query_tokens = technical_tokenize(query)
    ranked = []
    for document_id in candidate_document_ids:
        for row_index in rows_by_document[document_id]:
            record = chunk_records[row_index]
            ranked.append(
                RankedChunk(
                    row_index=row_index,
                    chunk_id=str(record["chunk_id"]),
                    document_id=document_id,
                    chunk_index=int(record["chunk_index"]),
                    body_start_char=int(record["body_start_char"]),
                    body_end_char=int(record["body_end_char"]),
                    score=statistics.score(query_tokens, passage_texts[row_index], row_index),
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
    documents = [
        RankedAggregatedDocument(document_id, item.score, item.chunk_id)
        for document_id, item in best_by_document.items()
    ]
    return ranked, documents
