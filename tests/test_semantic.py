import unittest

import numpy as np

from rag_confidence.retrieval.semantic import interval_union_covers, rank_candidate_chunks


class SemanticRankingTests(unittest.TestCase):
    def test_exact_chunk_ranking_and_document_max(self):
        embeddings = np.asarray([[1.0, 0.0], [0.8, 0.2], [0.0, 1.0]], dtype=np.float32)
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
        chunks, documents = rank_candidate_chunks(
            np.asarray([1.0, 0.0], dtype=np.float32),
            embeddings,
            records,
            {"a": [0, 1], "b": [2]},
            ["a", "b"],
        )
        self.assertEqual(["a::c0000", "a::c0001", "b::c0000"], [x.chunk_id for x in chunks])
        self.assertEqual(["a", "b"], [x.document_id for x in documents])
        self.assertEqual("a::c0000", documents[0].best_chunk_id)

    def test_interval_union_requires_continuous_coverage(self):
        self.assertTrue(interval_union_covers([(0, 6), (5, 12)], 2, 10))
        self.assertFalse(interval_union_covers([(0, 5), (6, 12)], 2, 10))
        self.assertFalse(interval_union_covers([], 2, 10))


if __name__ == "__main__":
    unittest.main()
