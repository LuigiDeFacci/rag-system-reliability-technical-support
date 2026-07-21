import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_confidence.data.audit import (  # noqa: E402
    audit_split,
    numeric_summary,
    question_fingerprint,
)


class DataAuditTest(unittest.TestCase):
    def test_numeric_summary(self) -> None:
        summary = numeric_summary([1, 2, 3, 4, 5])
        self.assertEqual(summary["count"], 5)
        self.assertEqual(summary["median"], 3)
        self.assertEqual(summary["maximum"], 5)

    def test_question_fingerprint_normalizes_case_and_whitespace(self) -> None:
        left = {"QUESTION_TITLE": "Error  42", "QUESTION_TEXT": "Fix IT"}
        right = {"QUESTION_TITLE": " error 42 ", "QUESTION_TEXT": "fix   it"}
        self.assertEqual(question_fingerprint(left), question_fingerprint(right))

    def test_split_audit_detects_span_mismatch(self) -> None:
        documents = {"doc-1": {"id": "doc-1", "text": "answer here"}}
        rows = [
            {
                "QUESTION_ID": "q-1",
                "QUESTION_TITLE": "Title",
                "QUESTION_TEXT": "Question",
                "DOC_IDS": ["doc-1"],
                "ANSWERABLE": "Y",
                "DOCUMENT": "doc-1",
                "START_OFFSET": "0",
                "END_OFFSET": "6",
                "ANSWER": "wrong!",
            }
        ]
        result = audit_split("synthetic", rows, documents)
        self.assertEqual(result["span_mismatches"], 1)
        self.assertEqual(result["span_mismatch_ids"], ["q-1"])


if __name__ == "__main__":
    unittest.main()
