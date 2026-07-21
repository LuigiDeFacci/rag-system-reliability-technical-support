import unittest

from rag_confidence.retrieval.rrf import reciprocal_rank_fusion
from rag_confidence.retrieval.semantic import RankedChunk


def item(chunk_id, document_id, score):
    return RankedChunk(0, chunk_id, document_id, 0, 0, 10, score)


class ReciprocalRankFusionTests(unittest.TestCase):
    def test_consensus_chunk_ranks_first(self):
        lexical = [item("a", "d1", 10), item("b", "d2", 9), item("c", "d3", 8)]
        semantic = [item("c", "d3", 1), item("a", "d1", 0.9), item("b", "d2", 0.8)]
        chunks, documents = reciprocal_rank_fusion(lexical, semantic, rrf_k=60)
        self.assertEqual("a", chunks[0].chunk_id)
        self.assertEqual("d1", documents[0].document_id)

    def test_mismatched_universes_are_rejected(self):
        with self.assertRaises(ValueError):
            reciprocal_rank_fusion([item("a", "d1", 1)], [item("b", "d2", 1)])


if __name__ == "__main__":
    unittest.main()
