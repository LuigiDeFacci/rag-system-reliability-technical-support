import unittest

from rag_confidence.retrieval.chunking import chunk_document, span_is_contained


class WhitespaceTokenizer:
    model_max_length = 12
    is_fast = True

    def __call__(self, text, *, add_special_tokens, return_offsets_mapping=False, **_):
        offsets = []
        cursor = 0
        for token in text.split():
            start = text.index(token, cursor)
            end = start + len(token)
            offsets.append((start, end))
            cursor = end
        result = {"input_ids": list(range(len(offsets) + (2 if add_special_tokens else 0)))}
        if return_offsets_mapping:
            result["offset_mapping"] = offsets
        return result


class ChunkingTests(unittest.TestCase):
    def test_windows_overlap_and_preserve_source_offsets(self):
        body = "zero one two three four five six seven eight nine"
        chunks = chunk_document(
            WhitespaceTokenizer(),
            "doc",
            "short title",
            body,
            body_size_tokens=5,
            overlap_tokens=2,
            title_max_tokens=2,
        )
        self.assertEqual(3, len(chunks))
        self.assertEqual(
            "zero one two three four", body[chunks[0].body_start_char : chunks[0].body_end_char]
        )
        self.assertEqual(
            "three four five six seven", body[chunks[1].body_start_char : chunks[1].body_end_char]
        )
        self.assertTrue(all(chunk.input_token_count <= 12 for chunk in chunks))

    def test_span_containment_is_strict(self):
        body = "zero one two three four five six seven"
        chunks = chunk_document(
            WhitespaceTokenizer(),
            "doc",
            "title",
            body,
            body_size_tokens=4,
            overlap_tokens=1,
            title_max_tokens=1,
        )
        start = body.index("three")
        end = body.index("five") + len("five")
        self.assertTrue(span_is_contained(chunks, start, end))
        self.assertFalse(span_is_contained(chunks[:1], start, end))

    def test_invalid_overlap_is_rejected(self):
        with self.assertRaises(ValueError):
            chunk_document(
                WhitespaceTokenizer(),
                "doc",
                "title",
                "body",
                body_size_tokens=4,
                overlap_tokens=4,
                title_max_tokens=1,
            )


if __name__ == "__main__":
    unittest.main()
