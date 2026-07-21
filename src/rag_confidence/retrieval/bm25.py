"""Small, transparent BM25 implementation for candidate-set reranking."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass


TOKEN_PATTERN = re.compile(r"(?u)\b\w+(?:[./:-]\w+)*\b")


def technical_tokenize(text: str) -> list[str]:
    """Lowercase text while preserving technical tokens such as versions and CVE IDs."""
    return [match.group(0).casefold() for match in TOKEN_PATTERN.finditer(text)]


@dataclass(frozen=True)
class RankedDocument:
    document_id: str
    score: float


class BM25Index:
    """BM25 corpus statistics with scoring restricted to supplied candidate IDs."""

    def __init__(
        self,
        documents: Iterable[tuple[str, str]],
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
        self.term_counts: dict[str, Counter[str]] = {}
        self.document_lengths: dict[str, int] = {}
        document_frequency: Counter[str] = Counter()

        for document_id, text in documents:
            if document_id in self.term_counts:
                raise ValueError(f"Duplicate document ID: {document_id}")
            counts = Counter(technical_tokenize(text))
            self.term_counts[document_id] = counts
            length = sum(counts.values())
            self.document_lengths[document_id] = length
            document_frequency.update(counts.keys())

        self.document_count = len(self.term_counts)
        if not self.document_count:
            raise ValueError("BM25 requires at least one document")
        self.average_document_length = sum(self.document_lengths.values()) / self.document_count
        self.idf = {
            term: math.log(1.0 + (self.document_count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def score(self, query_tokens: list[str], document_id: str) -> float:
        counts = self.term_counts[document_id]
        document_length = self.document_lengths[document_id]
        length_normalization = (
            1.0 - self.b + self.b * (document_length / self.average_document_length)
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

    def rank(self, query: str, candidate_ids: list[str]) -> list[RankedDocument]:
        query_tokens = technical_tokenize(query)
        missing = [
            document_id for document_id in candidate_ids if document_id not in self.term_counts
        ]
        if missing:
            raise KeyError(f"Candidate IDs missing from BM25 index: {missing[:5]}")
        scored = [
            (position, RankedDocument(document_id, self.score(query_tokens, document_id)))
            for position, document_id in enumerate(candidate_ids)
        ]
        scored.sort(key=lambda item: (-item[1].score, item[0], item[1].document_id))
        return [item[1] for item in scored]
