import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_confidence.retrieval.bm25 import BM25Index, technical_tokenize  # noqa: E402


class BM25Test(unittest.TestCase):
    def test_tokenizer_preserves_technical_identifiers(self) -> None:
        tokens = technical_tokenize("CVE-2016-6089 affects version 8.5.7.0 at /opt/IBM")
        self.assertIn("cve-2016-6089", tokens)
        self.assertIn("8.5.7.0", tokens)
        self.assertIn("opt/ibm", tokens)

    def test_matching_document_ranks_first(self) -> None:
        index = BM25Index(
            [
                ("a", "database timeout configuration"),
                ("b", "printer paper tray"),
            ]
        )
        ranking = index.rank("database timeout", ["b", "a"])
        self.assertEqual(ranking[0].document_id, "a")

    def test_candidate_order_breaks_score_ties(self) -> None:
        index = BM25Index([("a", "one"), ("b", "two")])
        ranking = index.rank("missing", ["b", "a"])
        self.assertEqual([item.document_id for item in ranking], ["b", "a"])


if __name__ == "__main__":
    unittest.main()
