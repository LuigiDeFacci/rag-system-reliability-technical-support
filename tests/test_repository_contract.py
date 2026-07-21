import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTest(unittest.TestCase):
    def test_final_test_gate_starts_closed(self) -> None:
        config = (ROOT / "configs" / "final_test.yaml").read_text(encoding="utf-8")
        self.assertRegex(config, re.compile(r"^allow_test:\s*false\s*$", re.MULTILINE))
        self.assertRegex(config, re.compile(r"^\s*protocol_frozen:\s*false\s*$", re.MULTILINE))

    def test_required_research_documents_exist(self) -> None:
        required = [
            "docs/research_protocol.md",
            "docs/instruction_review.md",
            "docs/data_audit.md",
            "docs/data_dictionary.md",
            "docs/decisions.md",
            "docs/experiment_registry.md",
            "docs/tcc_results_draft.md",
            "docs/test_access_log.md",
            "docs/semantic_retrieval.md",
            "docs/development_log.md",
            "docs/retrieval_results_internal.md",
            "docs/confidence_results_internal.md",
            "requirements-win-cuda.lock.txt",
        ]
        for relative_path in required:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())

    def test_results_draft_does_not_claim_final_test(self) -> None:
        text = (ROOT / "docs" / "tcc_results_draft.md").read_text(encoding="utf-8")
        self.assertIn("teste final não executado", text.lower())


if __name__ == "__main__":
    unittest.main()
