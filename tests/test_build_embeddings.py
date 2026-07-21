import unittest
from unittest.mock import patch

from rag_confidence.retrieval.build_embeddings import select_device


class DeviceSelectionTests(unittest.TestCase):
    @patch("rag_confidence.retrieval.build_embeddings.torch.cuda.is_available", return_value=False)
    def test_auto_falls_back_to_cpu(self, _):
        self.assertEqual("cpu", select_device("auto"))

    @patch("rag_confidence.retrieval.build_embeddings.torch.cuda.is_available", return_value=False)
    def test_explicit_cuda_fails_when_unavailable(self, _):
        with self.assertRaises(RuntimeError):
            select_device("cuda")


if __name__ == "__main__":
    unittest.main()
