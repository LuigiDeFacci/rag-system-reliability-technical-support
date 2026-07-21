import unittest

import pandas as pd

from rag_confidence.evaluation.evaluate_hard_negatives import (
    bootstrap_stress_intervals,
    summarize_negative_probabilities,
)


class HardNegativeEvaluationTests(unittest.TestCase):
    def test_false_acceptance_uses_frozen_thresholds(self) -> None:
        frame = pd.DataFrame({"probability": [0.1, 0.5, 0.9]})
        result = summarize_negative_probabilities(frame, {"balanced": 0.5})
        self.assertAlmostEqual(2 / 3, result["false_acceptance_rate"]["balanced"])
        self.assertAlmostEqual((0.01 + 0.25 + 0.81) / 3, result["brier_all_negative"])

    def test_empty_stress_set_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            summarize_negative_probabilities(pd.DataFrame({"probability": []}), {"x": 0.5})

    def test_bootstrap_rejects_duplicate_query_rows(self) -> None:
        comparison = pd.DataFrame(
            {
                "query_id": ["q1", "q1"],
                "probability": [0.2, 0.4],
                "probability_change_after_gold_removal": [-0.1, -0.2],
            }
        )
        with self.assertRaises(ValueError):
            bootstrap_stress_intervals(comparison, {"balanced": 0.3}, replicates=10, seed=42)


if __name__ == "__main__":
    unittest.main()
