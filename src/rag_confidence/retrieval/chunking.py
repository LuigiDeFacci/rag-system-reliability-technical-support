"""Tokenizer-aware document chunking with source-character provenance."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Protocol


class OffsetTokenizer(Protocol):
    model_max_length: int

    def __call__(self, text: str, **kwargs: Any) -> dict[str, Any]: ...


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    chunk_index: int
    passage_text: str
    body_start_char: int
    body_end_char: int
    body_token_count: int
    input_token_count: int

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def _offsets(tokenizer: OffsetTokenizer, text: str) -> list[tuple[int, int]]:
    encoded = tokenizer(
        text,
        add_special_tokens=False,
        return_attention_mask=False,
        return_token_type_ids=False,
        return_offsets_mapping=True,
        truncation=False,
        verbose=False,
    )
    offsets = [(int(start), int(end)) for start, end in encoded["offset_mapping"]]
    return [(start, end) for start, end in offsets if end > start]


def _input_length(tokenizer: OffsetTokenizer, text: str) -> int:
    encoded = tokenizer(
        text,
        add_special_tokens=True,
        return_attention_mask=False,
        return_token_type_ids=False,
        truncation=False,
        verbose=False,
    )
    return len(encoded["input_ids"])


def _truncate_title(tokenizer: OffsetTokenizer, title: str, max_tokens: int) -> str:
    offsets = _offsets(tokenizer, title)
    if len(offsets) <= max_tokens:
        return title.strip()
    return title[: offsets[max_tokens - 1][1]].strip()


def chunk_document(
    tokenizer: OffsetTokenizer,
    document_id: str,
    title: str,
    body: str,
    *,
    body_size_tokens: int = 448,
    overlap_tokens: int = 128,
    title_max_tokens: int = 56,
    model_max_length: int | None = None,
) -> list[DocumentChunk]:
    """Split a body into overlapping token windows while retaining source offsets."""
    if body_size_tokens <= 0:
        raise ValueError("body_size_tokens must be positive")
    if not 0 <= overlap_tokens < body_size_tokens:
        raise ValueError("overlap_tokens must be in [0, body_size_tokens)")
    if title_max_tokens <= 0:
        raise ValueError("title_max_tokens must be positive")

    effective_max = int(model_max_length or tokenizer.model_max_length)
    if effective_max <= 0 or effective_max > 1_000_000:
        raise ValueError("A finite positive model_max_length is required")

    passage_title = _truncate_title(tokenizer, title, title_max_tokens)
    body_offsets = _offsets(tokenizer, body)
    if not body_offsets:
        passage = passage_title
        return [
            DocumentChunk(
                chunk_id=f"{document_id}::c0000",
                document_id=document_id,
                chunk_index=0,
                passage_text=passage,
                body_start_char=0,
                body_end_char=0,
                body_token_count=0,
                input_token_count=_input_length(tokenizer, passage),
            )
        ]

    chunks: list[DocumentChunk] = []
    step = body_size_tokens - overlap_tokens
    start_token = 0
    while start_token < len(body_offsets):
        end_token = min(start_token + body_size_tokens, len(body_offsets))
        start_char = body_offsets[start_token][0]

        while True:
            end_char = body_offsets[end_token - 1][1]
            body_slice = body[start_char:end_char]
            passage = f"{passage_title}\n{body_slice}" if passage_title else body_slice
            input_token_count = _input_length(tokenizer, passage)
            if input_token_count <= effective_max:
                break
            end_token -= 1
            if end_token <= start_token:
                raise ValueError("Title leaves no room for a body token")

        chunk_index = len(chunks)
        chunks.append(
            DocumentChunk(
                chunk_id=f"{document_id}::c{chunk_index:04d}",
                document_id=document_id,
                chunk_index=chunk_index,
                passage_text=passage,
                body_start_char=start_char,
                body_end_char=end_char,
                body_token_count=end_token - start_token,
                input_token_count=input_token_count,
            )
        )
        if end_token == len(body_offsets):
            break
        next_start = start_token + step
        if next_start >= end_token:
            next_start = end_token
        start_token = next_start

    return chunks


def span_is_contained(chunks: Sequence[DocumentChunk], answer_start: int, answer_end: int) -> bool:
    """Return whether one body chunk fully contains a non-empty annotated span."""
    if answer_start < 0 or answer_end <= answer_start:
        return False
    return any(
        chunk.body_start_char <= answer_start and answer_end <= chunk.body_end_char
        for chunk in chunks
    )
