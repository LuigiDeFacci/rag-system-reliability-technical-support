import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_confidence.data.prepare import (  # noqa: E402
    assign_train_splits,
    canonical_question,
    deduplicate_preserving_order,
)


class DataPreparationTest(unittest.TestCase):
    def test_deduplicate_preserves_first_occurrence(self) -> None:
        self.assertEqual(deduplicate_preserving_order(["a", "b", "a"]), ["a", "b"])

    def test_grouped_split_keeps_identical_questions_together(self) -> None:
        rows = []
        for index in range(20):
            rows.append(
                {
                    "QUESTION_ID": f"q-{index}",
                    "QUESTION_TITLE": f"title {index // 2}",
                    "QUESTION_TEXT": f"body {index // 2}",
                    "ANSWERABLE": "Y" if index % 2 else "N",
                }
            )
        assignments = assign_train_splits(rows, seed=42)
        for index in range(0, 20, 2):
            self.assertEqual(assignments[f"q-{index}"], assignments[f"q-{index + 1}"])

    def test_canonical_question_deduplicates_candidates(self) -> None:
        row = {
            "QUESTION_ID": "q-1",
            "QUESTION_TITLE": "Title",
            "QUESTION_TEXT": "Body",
            "DOC_IDS": ["d-1", "d-1"],
            "ANSWERABLE": "Y",
            "DOCUMENT": "d-1",
            "START_OFFSET": "0",
            "END_OFFSET": "6",
            "ANSWER": "answer",
        }
        result = canonical_question(
            row,
            official_split="train",
            research_split="fit",
            train_fingerprints=set(),
            near_duplicate_ids=set(),
            documents={"d-1": {"text": "answer here"}},
        )
        self.assertEqual(result["candidate_doc_ids"], ["d-1"])
        self.assertTrue(result["candidates_deduplicated"])
        self.assertTrue(result["span_exact_match"])


if __name__ == "__main__":
    unittest.main()
