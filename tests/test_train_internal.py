import unittest

import numpy as np
import pandas as pd

from rag_confidence.models.train_internal import scenario_breakdown


class InternalTrainingTests(unittest.TestCase):
    def test_scenario_breakdown_is_evaluation_only(self):
        labels = pd.DataFrame(
            {
                "scenario_type": ["positive", "negative"],
                "evidence_sufficient": [True, False],
            }
        )
        result = scenario_breakdown(labels, np.asarray([0.8, 0.2]))
        self.assertEqual(1.0, result["positive"]["accuracy_at_0_5"])
        self.assertEqual(0.0, result["negative"]["positive_rate"])


if __name__ == "__main__":
    unittest.main()
