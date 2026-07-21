import unittest

import pandas as pd

from rag_confidence.scenarios.build_natural import build_records


class NaturalScenarioTests(unittest.TestCase):
    def test_labels_and_manifest_fields_follow_evaluation(self):
        questions = pd.DataFrame(
            [
                {
                    "query_id": "q1",
                    "research_split": "fit",
                    "answerable": True,
                    "gold_document_id": "gold",
                },
                {
                    "query_id": "q2",
                    "research_split": "fit",
                    "answerable": False,
                    "gold_document_id": None,
                },
            ]
        )
        rankings = pd.DataFrame(
            [
                {
                    "query_id": "q1",
                    "ranked_chunk_ids": ["gold::c0000"],
                    "ranked_chunk_document_ids": ["gold"],
                },
                {
                    "query_id": "q2",
                    "ranked_chunk_ids": ["other::c0000"],
                    "ranked_chunk_document_ids": ["other"],
                },
            ]
        )
        evaluations = pd.DataFrame(
            [
                {"query_id": "q1", "evidence_at_1": True},
                {"query_id": "q2", "evidence_at_1": False},
            ]
        )
        records = build_records(questions, rankings, evaluations, [1], "run", "commit", 42)
        self.assertEqual("natural_sufficient", records[0]["scenario_type"])
        self.assertEqual("native_unanswerable", records[1]["scenario_type"])
        self.assertIsNone(records[1]["relevant_document_id"])
        self.assertEqual([], records[0]["removed_document_ids"])


if __name__ == "__main__":
    unittest.main()
