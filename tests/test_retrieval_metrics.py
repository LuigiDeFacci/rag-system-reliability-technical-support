import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_confidence.evaluation.retrieval_metrics import (  # noqa: E402
    aggregate_retrieval_metrics,
)


class RetrievalMetricsTest(unittest.TestCase):
    def test_binary_relevance_metrics(self) -> None:
        metrics = aggregate_retrieval_metrics([1, 2, None], [1, 3])
        self.assertAlmostEqual(metrics["recall_at_1"], 1 / 3)
        self.assertAlmostEqual(metrics["recall_at_3"], 2 / 3)
        self.assertAlmostEqual(metrics["mrr"], 0.5)


if __name__ == "__main__":
    unittest.main()
