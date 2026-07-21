import unittest

import pandas as pd

from rag_confidence.features.build import (
    concordance_features,
    rank_correlation,
    score_distribution_features,
)


class FeatureExtractionTests(unittest.TestCase):
    def test_score_features_use_requested_cutoff(self):
        values = score_distribution_features("x", [4.0, 2.0, 1.0], ["a", "a", "b"], 2)
        self.assertEqual(3.0, values["x_topk_mean_raw"])
        self.assertEqual(0.5, values["x_topk_unique_document_ratio"])

    def test_rank_correlation_requires_same_universe(self):
        self.assertAlmostEqual(1.0, rank_correlation(["a", "b"], ["a", "b"]))
        self.assertAlmostEqual(-1.0, rank_correlation(["a", "b"], ["b", "a"]))
        with self.assertRaises(ValueError):
            rank_correlation(["a"], ["b"])

    def test_concordance_has_no_gold_inputs(self):
        def row(chunks, documents):
            return pd.Series({"ranked_chunk_ids": chunks, "ranked_chunk_document_ids": documents})

        values = concordance_features(
            row(["a", "b"], ["d1", "d2"]),
            row(["a", "b"], ["d1", "d2"]),
            row(["a", "b"], ["d1", "d2"]),
            2,
        )
        self.assertTrue(values["lex_sem_top1_chunk_agreement"])
        self.assertEqual(1.0, values["lex_sem_topk_chunk_jaccard"])


if __name__ == "__main__":
    unittest.main()
