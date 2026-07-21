import unittest

import pandas as pd

from rag_confidence.reporting.generate_final_report import error_analysis


class FinalReportingTests(unittest.TestCase):
    def test_error_analysis_uses_frozen_threshold(self) -> None:
        frame = pd.DataFrame(
            {
                "query_id": ["q1", "q2"],
                "scenario_type": ["miss", "sufficient"],
                "exact_duplicate_with_official_train": [False, False],
                "near_duplicate_with_official_train": [False, False],
                "evidence_sufficient": [False, True],
                "probability": [0.8, 0.2],
            }
        )
        result = error_analysis(frame, 0.5)
        observed = dict(zip(result["query_id"], result["error_type"], strict=True))
        self.assertEqual({"q2": "false_negative", "q1": "false_positive"}, observed)


if __name__ == "__main__":
    unittest.main()
