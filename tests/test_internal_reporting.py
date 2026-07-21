import unittest

import pandas as pd

from rag_confidence.reporting.generate_internal_report import error_table


class InternalReportingTest(unittest.TestCase):
    def test_error_table_uses_selected_threshold(self) -> None:
        predictions = pd.DataFrame(
            {
                "query_id": ["q1", "q2", "q3"],
                "scenario_id": ["s1", "s2", "s3"],
                "scenario_type": ["miss", "sufficient", "sufficient"],
                "context_k": [5, 5, 3],
                "method": ["raw", "raw", "raw"],
                "evidence_sufficient": [False, True, True],
                "probability": [0.8, 0.2, 0.9],
            }
        )
        result = error_table(predictions, cutoff=5, threshold=0.5)
        observed = dict(zip(result["query_id"], result["error_type"], strict=True))
        self.assertEqual(observed, {"q2": "false_negative", "q1": "false_positive"})


if __name__ == "__main__":
    unittest.main()
