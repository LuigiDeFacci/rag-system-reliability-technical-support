import unittest

import numpy as np

from rag_confidence.evaluation.run_prevalence_sensitivity import (
    prevalence_weights,
    weighted_summary,
)


class PrevalenceSensitivityTests(unittest.TestCase):
    def test_weights_encode_requested_prevalence(self) -> None:
        y = np.array([0, 0, 0, 1])
        weights = prevalence_weights(y, 0.6)
        self.assertAlmostEqual(1.0, weights.sum())
        self.assertAlmostEqual(0.6, weights[y == 1].sum())

    def test_perfect_probabilities_have_zero_weighted_error(self) -> None:
        y = np.array([0, 0, 1, 1])
        result = weighted_summary(y, y.astype(float), 0.2, {"balanced": 0.5})
        self.assertEqual(0.0, result["weighted_brier"])
        self.assertEqual(0.0, result["weighted_ece"])
        self.assertAlmostEqual(0.2, result["policies"]["balanced"]["coverage"])
        self.assertEqual(0.0, result["policies"]["balanced"]["selective_risk"])

    def test_invalid_target_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            prevalence_weights(np.array([0, 1]), 1.0)


if __name__ == "__main__":
    unittest.main()
