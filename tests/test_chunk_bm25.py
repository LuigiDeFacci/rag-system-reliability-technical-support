import unittest

from rag_confidence.retrieval.chunk_bm25 import (
    ChunkBM25Statistics,
    rank_bm25_candidate_chunks,
)


class ChunkBM25Tests(unittest.TestCase):
    def test_candidate_chunk_and_document_ranking(self):
        texts = ["error cve-2024-1 fix", "unrelated text", "error only"]
        records = [
            {
                "chunk_id": "a::c0000",
                "document_id": "a",
                "chunk_index": 0,
                "body_start_char": 0,
                "body_end_char": 10,
            },
            {
                "chunk_id": "a::c0001",
                "document_id": "a",
                "chunk_index": 1,
                "body_start_char": 8,
                "body_end_char": 18,
            },
            {
                "chunk_id": "b::c0000",
                "document_id": "b",
                "chunk_index": 0,
                "body_start_char": 0,
                "body_end_char": 10,
            },
        ]
        statistics = ChunkBM25Statistics(texts)
        chunks, documents = rank_bm25_candidate_chunks(
            "cve-2024-1 fix",
            texts,
            records,
            {"a": [0, 1], "b": [2]},
            ["a", "b"],
            statistics,
        )
        self.assertEqual("a::c0000", chunks[0].chunk_id)
        self.assertEqual("a", documents[0].document_id)


if __name__ == "__main__":
    unittest.main()
