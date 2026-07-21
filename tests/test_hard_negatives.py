import unittest

import pandas as pd

from rag_confidence.scenarios.build_hard_negatives import (
    build_records,
    conflict_note,
    top_non_gold_context,
)


class HardNegativeTests(unittest.TestCase):
    def test_top_non_gold_context_excludes_every_gold_chunk(self) -> None:
        ranking = pd.Series(
            {
                "ranked_chunk_ids": ["g1", "n1", "g2", "n2"],
                "ranked_chunk_document_ids": ["gold", "other1", "gold", "other2"],
                "ranked_chunk_scores": [4.0, 3.0, 2.0, 1.0],
            }
        )
        context = top_non_gold_context(ranking, "gold", 2)
        self.assertEqual(["n1", "n2"], context["included_chunk_ids"])
        self.assertNotIn("gold", context["included_document_ids"])
        self.assertEqual([2, 4], context["source_chunk_ranks"])

    def test_conflict_note_requires_disjoint_observable_patterns(self) -> None:
        self.assertIsNotNone(conflict_note("DB2 9.7 error SQL1234", "DB2 10.5 error SQL9999"))
        self.assertIsNone(conflict_note("DB2 9.7 error SQL1234", "Fix for DB2 9.7 SQL1234"))

    def test_record_label_does_not_depend_on_scores(self) -> None:
        questions = pd.DataFrame(
            [
                {
                    "query_id": "q1",
                    "research_split": "fit",
                    "answerable": True,
                    "gold_document_id": "gold",
                    "query_text": "Product 1.0 error ABC123",
                }
            ]
        )
        ranking = pd.DataFrame(
            [
                {
                    "query_id": "q1",
                    "ranked_chunk_ids": ["gold::c0000", "other::c0000"],
                    "ranked_chunk_document_ids": ["gold", "other"],
                    "ranked_chunk_scores": [100.0, -100.0],
                    "ranked_chunk_body_starts": [0, 0],
                    "ranked_chunk_body_ends": [10, 10],
                }
            ]
        )
        chunks = pd.DataFrame(
            [
                {"chunk_id": "gold::c0000", "passage_text": "gold"},
                {"chunk_id": "other::c0000", "passage_text": "Product 2.0 error XYZ999"},
            ]
        )
        documents = pd.DataFrame(
            [
                {"document_id": "gold", "product_name": "A"},
                {"document_id": "other", "product_name": "B"},
            ]
        )
        records = build_records(
            questions,
            {"bm25": ranking, "semantic": ranking},
            chunks,
            documents,
            cutoff=1,
            seed=42,
            source_run_ids={"bm25": "b", "semantic": "s"},
            code_commit="commit",
        )
        self.assertEqual(3, len(records))
        self.assertTrue(all(row["evidence_sufficient"] is False for row in records))
        self.assertTrue(all(row["removed_document_ids"] == ["gold"] for row in records))


if __name__ == "__main__":
    unittest.main()
