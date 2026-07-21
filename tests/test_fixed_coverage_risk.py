import unittest

import numpy as np

from rag_confidence.evaluation.run_fixed_coverage_risk import tie_aware_risk_at_coverage


class FixedCoverageRiskTests(unittest.TestCase):
    def test_exact_coverage_without_ties(self) -> None:
        result = tie_aware_risk_at_coverage(
            np.array([1, 0, 1, 0]), np.array([0.9, 0.8, 0.7, 0.6]), 0.5
        )
        self.assertEqual(2.0, result["accepted_mass"])
        self.assertEqual(0.5, result["risk"])

    def test_boundary_tie_is_fractional_and_order_invariant(self) -> None:
        labels = np.array([1, 1, 0, 0])
        scores = np.array([0.9, 0.5, 0.5, 0.5])
        result = tie_aware_risk_at_coverage(labels, scores, 0.5)
        permuted = tie_aware_risk_at_coverage(labels[::-1], scores[::-1], 0.5)
        self.assertAlmostEqual(1 / 3, result["risk"])
        self.assertAlmostEqual(result["risk"], permuted["risk"])
        self.assertEqual(3, result["boundary_tie_count"])
        self.assertAlmostEqual(1 / 3, result["boundary_fraction"])

    def test_invalid_coverage_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            tie_aware_risk_at_coverage(np.array([0, 1]), np.array([0.2, 0.8]), 0.0)


if __name__ == "__main__":
    unittest.main()
