import unittest

import pandas as pd

from rag_confidence.evaluation.run_final_test import evaluate_subset


class FinalEvaluationTests(unittest.TestCase):
    def test_subset_applies_frozen_policy_and_baseline_thresholds(self) -> None:
        frame = pd.DataFrame(
            {
                "evidence_sufficient": [False, True, False, True],
                "probability": [0.1, 0.9, 0.8, 0.7],
                "signal": [0.1, 0.9, 0.8, 0.7],
            }
        )
        result = evaluate_subset(
            frame,
            {"balanced": 0.75},
            {"baseline": {"signal": "signal", "threshold": 0.75}},
            ece_bins=2,
        )
        self.assertEqual(4, result["rows"])
        self.assertEqual([[1, 1], [1, 1]], result["policies"]["balanced"]["confusion_matrix"])
        self.assertEqual(
            result["policies"]["balanced"]["confusion_matrix"],
            result["baselines"]["baseline"]["frozen_threshold"]["confusion_matrix"],
        )


if __name__ == "__main__":
    unittest.main()
