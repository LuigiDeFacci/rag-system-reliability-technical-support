import unittest

import numpy as np

from rag_confidence.evaluation.confidence_metrics import (
    best_f1_threshold,
    classification_metrics,
    expected_calibration_error,
    selective_summary,
    threshold_for_maximum_coverage_at_risk,
)


class ConfidenceMetricsTests(unittest.TestCase):
    def setUp(self):
        self.y = np.asarray([1, 1, 0, 0])
        self.p = np.asarray([0.9, 0.8, 0.2, 0.1])

    def test_perfect_separation_metrics(self):
        metrics = classification_metrics(self.y, self.p, 0.5)
        self.assertEqual(1.0, metrics["f1"])
        self.assertEqual([[2, 0], [0, 2]], metrics["confusion_matrix"])
        self.assertEqual(1.0, best_f1_threshold(self.y, self.p)["f1"])

    def test_ece_uses_equal_width_bins(self):
        ece, bins = expected_calibration_error(self.y, self.p, n_bins=2)
        self.assertAlmostEqual(0.15, ece)
        self.assertEqual(2, len(bins))

    def test_selective_risk_and_coverage(self):
        summary = selective_summary(self.y, self.p)
        self.assertEqual(0.0, summary["risk_at_coverage"]["0.5"])
        point = threshold_for_maximum_coverage_at_risk(self.y, self.p, 0.0)
        self.assertEqual(0.5, point["coverage"])


if __name__ == "__main__":
    unittest.main()
