"""Audit the locally extracted TechQA release without changing raw files.

The audit is deliberately read-only. It checks the release boundary before
retrieval code runs: hashes, schema, alignment, candidates, answer spans,
class counts and cross-split duplication. Its JSON manifest documents inputs;
it is not a model feature.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest used to identify an input artifact."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_text(value: str) -> str:
    return " ".join(value.casefold().split())


def question_text(row: dict[str, Any]) -> str:
    return f"{row.get('QUESTION_TITLE', '')}\n{row.get('QUESTION_TEXT', '')}"


def question_fingerprint(row: dict[str, Any]) -> str:
    """Create a stable grouping key from normalized title and question text."""
    return hashlib.sha256(normalized_text(question_text(row)).encode("utf-8")).hexdigest()


def as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def numeric_summary(values: list[int]) -> dict[str, float | int]:
    if not values:
        return {"count": 0}
    ordered = sorted(values)

    def percentile(fraction: float) -> int:
        index = round((len(ordered) - 1) * fraction)
        return ordered[index]

    return {
        "count": len(ordered),
        "minimum": ordered[0],
        "p25": percentile(0.25),
        "median": percentile(0.50),
        "p75": percentile(0.75),
        "p95": percentile(0.95),
        "maximum": ordered[-1],
        "mean": sum(ordered) / len(ordered),
    }


def git_commit(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def audit_documents(documents: dict[str, dict[str, Any]]) -> dict[str, Any]:
    field_counts: Counter[str] = Counter()
    metadata_counts: Counter[str] = Counter()
    text_hash_to_ids: defaultdict[str, list[str]] = defaultdict(list)
    empty_text = 0
    id_mismatches = 0
    text_lengths: list[int] = []
    nonempty_metadata: Counter[str] = Counter()
    product_names: set[str] = set()
    product_ids: set[str] = set()

    for key, document in documents.items():
        field_counts.update(document.keys())
        metadata = document.get("metadata") or {}
        metadata_counts.update(metadata.keys())
        for key, value in metadata.items():
            if value not in (None, "", [], {}):
                nonempty_metadata[key] += 1
        if metadata.get("productName"):
            product_names.add(str(metadata["productName"]))
        if metadata.get("productId"):
            product_ids.add(str(metadata["productId"]))
        text = document.get("text") or ""
        text_lengths.append(len(text))
        if not text.strip():
            empty_text += 1
        else:
            digest = hashlib.sha256(normalized_text(text).encode("utf-8")).hexdigest()
            text_hash_to_ids[digest].append(key)
        if str(document.get("id")) != str(key):
            id_mismatches += 1

    duplicate_groups = [ids for ids in text_hash_to_ids.values() if len(ids) > 1]
    return {
        "count": len(documents),
        "field_coverage": dict(sorted(field_counts.items())),
        "metadata_coverage": dict(sorted(metadata_counts.items())),
        "metadata_nonempty": dict(sorted(nonempty_metadata.items())),
        "unique_product_names": len(product_names),
        "unique_product_ids": len(product_ids),
        "text_length_characters": numeric_summary(text_lengths),
        "empty_text": empty_text,
        "id_mismatches": id_mismatches,
        "duplicate_text_groups": len(duplicate_groups),
        "documents_in_duplicate_text_groups": sum(len(ids) for ids in duplicate_groups),
        "largest_duplicate_group": max((len(ids) for ids in duplicate_groups), default=1),
    }


def audit_split(
    name: str,
    rows: list[dict[str, Any]],
    documents: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    ids = [str(row.get("QUESTION_ID")) for row in rows]
    field_sets = Counter(tuple(sorted(row.keys())) for row in rows)
    answerability = Counter(str(row.get("ANSWERABLE")) for row in rows)
    candidate_counts: list[int] = []
    missing_candidate_documents = 0
    gold_not_in_candidates = 0
    missing_gold_documents = 0
    invalid_offsets = 0
    span_mismatches = 0
    invalid_offset_ids: list[str] = []
    span_mismatch_ids: list[str] = []
    invalid_unanswerable_placeholders = 0
    duplicate_candidate_ids = 0
    candidate_count_outliers: list[dict[str, Any]] = []
    answer_span_lengths: list[int] = []
    answer_field_lengths: list[int] = []
    question_lengths: list[int] = []
    gold_document_counts: Counter[str] = Counter()
    fingerprint_to_ids: defaultdict[str, list[str]] = defaultdict(list)
    fingerprint_to_labels: defaultdict[str, set[str]] = defaultdict(set)

    for row in rows:
        candidate_ids = [str(value) for value in (row.get("DOC_IDS") or [])]
        candidate_counts.append(len(candidate_ids))
        if len(candidate_ids) != 50:
            candidate_count_outliers.append(
                {"query_id": str(row.get("QUESTION_ID")), "count": len(candidate_ids)}
            )
        if len(candidate_ids) != len(set(candidate_ids)):
            duplicate_candidate_ids += 1
        question_lengths.append(len(question_text(row)))
        fingerprint_to_ids[question_fingerprint(row)].append(str(row.get("QUESTION_ID")))
        fingerprint_to_labels[question_fingerprint(row)].add(str(row.get("ANSWERABLE")))
        missing_candidate_documents += sum(doc_id not in documents for doc_id in candidate_ids)

        if row.get("ANSWERABLE") == "Y":
            gold_id = str(row.get("DOCUMENT"))
            gold_document_counts[gold_id] += 1
            answer_field_lengths.append(len(str(row.get("ANSWER") or "")))
            if gold_id not in candidate_ids:
                gold_not_in_candidates += 1
            document = documents.get(gold_id)
            if document is None:
                missing_gold_documents += 1
                continue
            start = as_int(row.get("START_OFFSET"))
            end = as_int(row.get("END_OFFSET"))
            text = document.get("text") or ""
            if start is None or end is None or start < 0 or end < start or end > len(text):
                invalid_offsets += 1
                invalid_offset_ids.append(str(row.get("QUESTION_ID")))
            elif text[start:end] != row.get("ANSWER"):
                span_mismatches += 1
                span_mismatch_ids.append(str(row.get("QUESTION_ID")))
            if start is not None and end is not None and end >= start:
                answer_span_lengths.append(end - start)
        else:
            placeholders = (
                row.get("DOCUMENT"),
                row.get("ANSWER"),
                row.get("START_OFFSET"),
                row.get("END_OFFSET"),
            )
            if any(value != "-" for value in placeholders):
                invalid_unanswerable_placeholders += 1

    candidate_summary = {
        "minimum": min(candidate_counts, default=0),
        "maximum": max(candidate_counts, default=0),
        "mean": sum(candidate_counts) / len(candidate_counts) if candidate_counts else 0,
        "distribution": dict(sorted(Counter(candidate_counts).items())),
    }
    return {
        "name": name,
        "count": len(rows),
        "unique_question_ids": len(set(ids)),
        "duplicate_question_ids": len(ids) - len(set(ids)),
        "answerability": dict(sorted(answerability.items())),
        "field_sets": {"|".join(fields): count for fields, count in field_sets.items()},
        "candidate_count": candidate_summary,
        "candidate_count_outliers": candidate_count_outliers,
        "queries_with_duplicate_candidate_ids": duplicate_candidate_ids,
        "unique_candidate_documents": len(
            {str(doc_id) for row in rows for doc_id in (row.get("DOC_IDS") or [])}
        ),
        "question_length_characters": numeric_summary(question_lengths),
        "answer_span_length_characters": numeric_summary(answer_span_lengths),
        "answer_field_length_characters": numeric_summary(answer_field_lengths),
        "unique_gold_documents": len(gold_document_counts),
        "reused_gold_documents": sum(count > 1 for count in gold_document_counts.values()),
        "exact_duplicate_question_groups_within_split": sum(
            len(group) > 1 for group in fingerprint_to_ids.values()
        ),
        "exact_duplicate_groups_with_label_conflicts": sum(
            len(fingerprint_to_ids[fingerprint]) > 1 and len(labels) > 1
            for fingerprint, labels in fingerprint_to_labels.items()
        ),
        "missing_candidate_document_references": missing_candidate_documents,
        "gold_not_in_candidates": gold_not_in_candidates,
        "missing_gold_documents": missing_gold_documents,
        "invalid_offsets": invalid_offsets,
        "invalid_offset_ids": invalid_offset_ids,
        "span_mismatches": span_mismatches,
        "span_mismatch_ids": span_mismatch_ids,
        "invalid_unanswerable_placeholders": invalid_unanswerable_placeholders,
    }


def pairwise_overlap(
    left_name: str,
    left: list[dict[str, Any]],
    right_name: str,
    right: list[dict[str, Any]],
) -> dict[str, Any]:
    left_ids = {str(row.get("QUESTION_ID")) for row in left}
    right_ids = {str(row.get("QUESTION_ID")) for row in right}
    left_fingerprints: defaultdict[str, list[str]] = defaultdict(list)
    right_fingerprints: defaultdict[str, list[str]] = defaultdict(list)
    for row in left:
        left_fingerprints[question_fingerprint(row)].append(str(row.get("QUESTION_ID")))
    for row in right:
        right_fingerprints[question_fingerprint(row)].append(str(row.get("QUESTION_ID")))
    shared_fingerprints = set(left_fingerprints) & set(right_fingerprints)
    examples = []
    matched_pairs = 0
    label_conflicts = 0
    for fingerprint in sorted(shared_fingerprints)[:25]:
        examples.append(
            {
                "left_ids": left_fingerprints[fingerprint],
                "right_ids": right_fingerprints[fingerprint],
            }
        )
    left_rows = defaultdict(list)
    right_rows = defaultdict(list)
    for row in left:
        left_rows[question_fingerprint(row)].append(row)
    for row in right:
        right_rows[question_fingerprint(row)].append(row)
    for fingerprint in shared_fingerprints:
        for left_row in left_rows[fingerprint]:
            for right_row in right_rows[fingerprint]:
                matched_pairs += 1
                if left_row.get("ANSWERABLE") != right_row.get("ANSWERABLE"):
                    label_conflicts += 1
    return {
        "pair": f"{left_name}__{right_name}",
        "shared_question_ids": len(left_ids & right_ids),
        "exact_question_text_matches": len(shared_fingerprints),
        "exact_question_pair_count": matched_pairs,
        "answerability_label_conflicts": label_conflicts,
        "examples": examples,
    }


def near_duplicate_overlaps(
    splits: dict[str, list[dict[str, Any]]], threshold: float = 0.90
) -> list[dict[str, Any]]:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    names = list(splits)
    rows = [row for name in names for row in splits[name]]
    texts = [question_text(row) for row in rows]
    matrix = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        lowercase=True,
        strip_accents="unicode",
        sublinear_tf=True,
        max_features=50_000,
    ).fit_transform(texts)

    offsets: dict[str, tuple[int, int]] = {}
    cursor = 0
    for name in names:
        offsets[name] = (cursor, cursor + len(splits[name]))
        cursor += len(splits[name])

    results = []
    for left_index, left_name in enumerate(names):
        for right_name in names[left_index + 1 :]:
            left_start, left_end = offsets[left_name]
            right_start, right_end = offsets[right_name]
            similarities = cosine_similarity(
                matrix[left_start:left_end], matrix[right_start:right_end], dense_output=True
            )
            candidates = []
            for left_row, right_row in zip(*((similarities >= threshold).nonzero())):
                score = float(similarities[left_row, right_row])
                candidates.append(
                    {
                        "left_id": str(splits[left_name][left_row].get("QUESTION_ID")),
                        "right_id": str(splits[right_name][right_row].get("QUESTION_ID")),
                        "similarity": round(score, 6),
                        "exact": question_fingerprint(splits[left_name][left_row])
                        == question_fingerprint(splits[right_name][right_row]),
                    }
                )
            candidates.sort(
                key=lambda item: (-item["similarity"], item["left_id"], item["right_id"])
            )
            results.append(
                {
                    "pair": f"{left_name}__{right_name}",
                    "threshold": threshold,
                    "count": len(candidates),
                    "unique_left_queries": len({item["left_id"] for item in candidates}),
                    "unique_right_queries": len({item["right_id"] for item in candidates}),
                    "pairs": candidates[:100],
                    "truncated": len(candidates) > 100,
                }
            )
    return results


def candidate_document_overlap(splits: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    document_sets = {
        name: {str(doc_id) for row in rows for doc_id in (row.get("DOC_IDS") or [])}
        for name, rows in splits.items()
    }
    names = list(splits)
    results = []
    for left_index, left_name in enumerate(names):
        for right_name in names[left_index + 1 :]:
            shared = document_sets[left_name] & document_sets[right_name]
            results.append(
                {
                    "pair": f"{left_name}__{right_name}",
                    "left_unique_documents": len(document_sets[left_name]),
                    "right_unique_documents": len(document_sets[right_name]),
                    "shared_documents": len(shared),
                }
            )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data/raw/TechQA"))
    parser.add_argument("--archive", type=Path, default=Path("data/raw/TechQA.tar.gz"))
    parser.add_argument("--output", type=Path, default=Path("data/manifests/techqa_audit.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path.cwd().resolve()
    data_root = args.data_root.resolve()
    files = {
        "train": data_root / "training_and_dev" / "training_Q_A.json",
        "dev": data_root / "training_and_dev" / "dev_Q_A.json",
        "train_dev_documents": data_root / "training_and_dev" / "training_dev_technotes.json",
        "validation_questions": data_root / "validation" / "validation_questions.json",
        "validation_reference": data_root / "validation" / "validation_reference.json",
        "validation_documents": data_root / "validation" / "validation_technotes.json",
        "readme": data_root / "README.txt",
        "license": data_root / "CDLA-Permissive-v1.0.pdf",
    }
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing required files: {missing}")

    with files["train"].open(encoding="utf-8") as stream:
        train = json.load(stream)
    with files["dev"].open(encoding="utf-8") as stream:
        dev = json.load(stream)
    with files["validation_questions"].open(encoding="utf-8") as stream:
        validation_questions = json.load(stream)
    with files["validation_reference"].open(encoding="utf-8") as stream:
        validation_reference = json.load(stream)
    with files["train_dev_documents"].open(encoding="utf-8") as stream:
        train_dev_documents = json.load(stream)
    with files["validation_documents"].open(encoding="utf-8") as stream:
        validation_documents = json.load(stream)

    validation_questions_by_id = {str(row["QUESTION_ID"]): row for row in validation_questions}
    validation_alignment_errors = 0
    for reference in validation_reference:
        question = validation_questions_by_id.get(str(reference.get("QUESTION_ID")))
        if question is None:
            validation_alignment_errors += 1
            continue
        for field in ("QUESTION_TITLE", "QUESTION_TEXT", "DOC_IDS"):
            if question.get(field) != reference.get(field):
                validation_alignment_errors += 1
                break

    splits = {"train": train, "dev": dev, "validation": validation_reference}
    overlap_results = []
    split_names = list(splits)
    for left_index, left_name in enumerate(split_names):
        for right_name in split_names[left_index + 1 :]:
            overlap_results.append(
                pairwise_overlap(left_name, splits[left_name], right_name, splits[right_name])
            )

    audit = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "git_commit": git_commit(root),
        "source": {
            "url": "https://huggingface.co/datasets/PrimeQA/TechQA",
            "archive_size": args.archive.stat().st_size,
            "archive_sha256": sha256_file(args.archive),
            "dataset_license": "CDLA-Permissive-1.0",
        },
        "files": {
            name: {
                "path": str(path.relative_to(root)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for name, path in files.items()
        },
        "splits": {
            "train": audit_split("train", train, train_dev_documents),
            "dev": audit_split("dev", dev, train_dev_documents),
            "validation": audit_split("validation", validation_reference, validation_documents),
        },
        "documents": {
            "train_dev": audit_documents(train_dev_documents),
            "validation": audit_documents(validation_documents),
        },
        "validation_question_reference_alignment_errors": validation_alignment_errors,
        "exact_question_overlap": overlap_results,
        "near_duplicate_question_overlap": near_duplicate_overlaps(splits),
        "candidate_document_overlap": candidate_document_overlap(splits),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as stream:
        json.dump(audit, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(f"WROTE={args.output.resolve()}")
    for name, split_audit in audit["splits"].items():
        print(
            f"{name}: count={split_audit['count']} "
            f"answerability={split_audit['answerability']} "
            f"span_mismatches={split_audit['span_mismatches']}"
        )


if __name__ == "__main__":
    main()
