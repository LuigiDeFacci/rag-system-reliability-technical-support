import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rag_confidence.retrieval.run_bm25 import enforce_test_gate  # noqa: E402


class FinalTestGateTest(unittest.TestCase):
    def test_flag_is_required(self) -> None:
        with self.assertRaises(PermissionError):
            enforce_test_gate(("final_test",), allow_test=False, gate_path=Path("unused"))

    def test_locked_configuration_rejects_test(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            gate = Path(directory) / "gate.yaml"
            gate.write_text(
                "allow_test: false\nrequirements:\n  protocol_frozen: false\n",
                encoding="utf-8",
            )
            with self.assertRaises(PermissionError):
                enforce_test_gate(("final_test",), allow_test=True, gate_path=gate)

    def test_non_test_splits_do_not_read_gate(self) -> None:
        enforce_test_gate(("fit", "selection"), allow_test=False, gate_path=Path("missing"))


if __name__ == "__main__":
    unittest.main()
