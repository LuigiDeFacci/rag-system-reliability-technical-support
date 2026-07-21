import unittest

import pandas as pd

from rag_confidence.evaluation.context_retrieval import evaluate_context_rankings


class ContextRetrievalEvaluationTests(unittest.TestCase):
    def test_union_of_two_gold_chunks_can_supply_evidence(self):
        questions = pd.DataFrame(
            [
                {
                    "query_id": "q1",
                    "research_split": "fit",
                    "answerable": True,
                    "gold_document_id": "gold",
                    "answer_start": 2,
                    "answer_end": 10,
                }
            ]
        )
        rankings = pd.DataFrame(
            [
                {
                    "query_id": "q1",
                    "ranked_chunk_document_ids": ["gold", "gold", "other"],
                    "ranked_chunk_body_starts": [0, 5, 0],
                    "ranked_chunk_body_ends": [6, 12, 5],
                    "ranked_document_ids": ["gold", "other"],
                }
            ]
        )
        evaluation, metrics = evaluate_context_rankings(questions, rankings, [1, 2])
        self.assertFalse(bool(evaluation.loc[0, "evidence_at_1"]))
        self.assertTrue(bool(evaluation.loc[0, "evidence_at_2"]))
        self.assertEqual(1.0, metrics["fit"]["answerable_context_recall_at_2"])


if __name__ == "__main__":
    unittest.main()
