import unittest

import numpy as np

from rag_confidence.evaluation.run_robustness import (
    grouped_bootstrap_indices,
    paired_bootstrap_difference,
)


class RobustnessTests(unittest.TestCase):
    def test_grouped_indices_keep_cluster_rows_together(self):
        query_ids = np.asarray(["a", "a", "b", "b"])
        indices = grouped_bootstrap_indices(query_ids, np.random.default_rng(2))
        self.assertEqual(4, len(indices))
        for start in range(0, len(indices), 2):
            self.assertEqual(query_ids[indices[start]], query_ids[indices[start + 1]])

    def test_paired_difference_is_positive_for_better_scores(self):
        y = np.asarray([1, 1, 0, 0])
        proposed = np.asarray([0.9, 0.8, 0.2, 0.1])
        baseline = np.asarray([0.6, 0.4, 0.7, 0.3])
        summary, values = paired_bootstrap_difference(
            y,
            proposed,
            baseline,
            np.asarray(["a", "b", "c", "d"]),
            lambda truth, score: float(((truth == 1) == (score >= 0.5)).mean()),
            replicates=100,
            seed=42,
        )
        self.assertGreater(summary["observed_improvement"], 0)
        self.assertTrue(len(values) > 0)


if __name__ == "__main__":
    unittest.main()
