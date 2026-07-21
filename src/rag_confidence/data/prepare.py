"""Create a canonical, leakage-aware TechQA dataset from immutable raw files."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from rag_confidence.data.audit import question_fingerprint, sha256_file


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def deduplicate_preserving_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values))


def assign_train_splits(rows: list[dict[str, Any]], seed: int) -> dict[str, str]:
    group_rows: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        group_rows[question_fingerprint(row)].append(row)

    grouped_counts = []
    for group, members in group_rows.items():
        counts = np.asarray(
            [
                sum(member["ANSWERABLE"] == "N" for member in members),
                sum(member["ANSWERABLE"] == "Y" for member in members),
            ],
            dtype=np.int64,
        )
        grouped_counts.append((group, counts))

    rng = random.Random(seed)
    rng.shuffle(grouped_counts)
    grouped_counts.sort(key=lambda item: -float(np.std(item[1])))
    total_by_class = np.asarray(
        [
            sum(row["ANSWERABLE"] == "N" for row in rows),
            sum(row["ANSWERABLE"] == "Y" for row in rows),
        ],
        dtype=np.float64,
    )
    fold_counts = [np.zeros(2, dtype=np.int64) for _ in range(5)]
    fold_groups: list[list[str]] = [[] for _ in range(5)]

    for group, counts in grouped_counts:
        best: tuple[float, int, int] | None = None
        for fold in range(5):
            fold_counts[fold] += counts
            class_balance = float(
                np.mean(
                    [
                        np.std([current[label] / total_by_class[label] for current in fold_counts])
                        for label in range(2)
                    ]
                )
            )
            size_penalty = abs(int(fold_counts[fold].sum()) - len(rows) / 5) / len(rows)
            fold_counts[fold] -= counts
            candidate = (class_balance + 0.02 * size_penalty, len(fold_groups[fold]), fold)
            if best is None or candidate < best:
                best = candidate
        assert best is not None
        selected_fold = best[2]
        fold_counts[selected_fold] += counts
        fold_groups[selected_fold].append(group)

    fold_by_group = {group: fold for fold, groups in enumerate(fold_groups) for group in groups}
    fold_by_query = {
        str(row["QUESTION_ID"]): fold_by_group[question_fingerprint(row)] for row in rows
    }
    fold_to_split = {0: "calibration", 1: "selection", 2: "fit", 3: "fit", 4: "fit"}
    return {query_id: fold_to_split[fold] for query_id, fold in fold_by_query.items()}


def near_duplicate_dev_ids(audit_manifest: dict[str, Any]) -> set[str]:
    for item in audit_manifest["near_duplicate_question_overlap"]:
        if item["pair"] == "train__dev":
            if item.get("truncated"):
                raise RuntimeError("Near-duplicate manifest was truncated; refusing partial flags.")
            return {str(pair["right_id"]) for pair in item["pairs"]}
    raise KeyError("The audit manifest has no train__dev near-duplicate analysis.")


def canonical_question(
    row: dict[str, Any],
    official_split: str,
    research_split: str,
    train_fingerprints: set[str],
    near_duplicate_ids: set[str],
    documents: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    query_id = str(row["QUESTION_ID"])
    raw_candidates = [str(value) for value in row["DOC_IDS"]]
    candidates = deduplicate_preserving_order(raw_candidates)
    missing = [document_id for document_id in candidates if document_id not in documents]
    if missing:
        raise ValueError(f"{query_id} references missing candidate documents: {missing[:5]}")

    answerable = row["ANSWERABLE"] == "Y"
    gold_document_id = str(row["DOCUMENT"]) if answerable else None
    answer_start = int(row["START_OFFSET"]) if answerable else None
    answer_end = int(row["END_OFFSET"]) if answerable else None
    answer_text = str(row["ANSWER"]) if answerable else None
    if answerable:
        document_text = documents[gold_document_id]["text"]
        span_exact_match = document_text[answer_start:answer_end] == answer_text
    else:
        span_exact_match = None

    fingerprint = question_fingerprint(row)
    return {
        "query_id": query_id,
        "official_split": official_split,
        "research_split": research_split,
        "question_group_id": f"qg_{fingerprint[:20]}",
        "question_title": str(row["QUESTION_TITLE"]),
        "question_text": str(row["QUESTION_TEXT"]),
        "query_text": f"{row['QUESTION_TITLE']}\n{row['QUESTION_TEXT']}",
        "candidate_doc_ids": candidates,
        "candidate_count_raw": len(raw_candidates),
        "candidate_count_unique": len(candidates),
        "candidates_deduplicated": len(raw_candidates) != len(candidates),
        "answerable": answerable,
        "gold_document_id": gold_document_id,
        "answer_start": answer_start,
        "answer_end": answer_end,
        "answer_text": answer_text,
        "span_exact_match": span_exact_match,
        "exact_duplicate_with_official_train": (
            official_split == "dev" and fingerprint in train_fingerprints
        ),
        "near_duplicate_with_official_train": (
            official_split == "dev" and query_id in near_duplicate_ids
        ),
    }


def merge_documents(
    primary: dict[str, dict[str, Any]], secondary: dict[str, dict[str, Any]]
) -> tuple[dict[str, dict[str, Any]], int]:
    merged = dict(primary)
    conflicts = 0
    for document_id, document in secondary.items():
        if document_id in merged:
            if merged[document_id].get("text") != document.get("text"):
                conflicts += 1
        else:
            merged[document_id] = document
    return merged, conflicts


def document_records(documents: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for document_id in sorted(documents):
        document = documents[document_id]
        metadata = document.get("metadata") or {}
        records.append(
            {
                "document_id": document_id,
                "title": str(document.get("title") or ""),
                "text": str(document.get("text") or ""),
                "product_id": str(metadata.get("productId") or ""),
                "product_name": str(metadata.get("productName") or ""),
                "date": str(metadata.get("date") or ""),
                "canonical_url": str(metadata.get("canonicalUrl") or ""),
                "source_document_id": str(metadata.get("sourceDocumentId") or ""),
            }
        )
    return records


def split_summary(questions: pd.DataFrame) -> dict[str, Any]:
    summary = {}
    for split, frame in questions.groupby("research_split", sort=True):
        summary[str(split)] = {
            "count": int(len(frame)),
            "answerable": int(frame["answerable"].sum()),
            "unanswerable": int((~frame["answerable"]).sum()),
            "question_groups": int(frame["question_group_id"].nunique()),
        }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=Path("data/raw/TechQA"))
    parser.add_argument(
        "--audit-manifest", type=Path, default=Path("data/manifests/techqa_audit.json")
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/techqa_v1"))
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path.cwd().resolve()
    data_root = args.data_root.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite processed data: {output_dir}. Use a new versioned directory."
        )

    train_path = data_root / "training_and_dev" / "training_Q_A.json"
    dev_path = data_root / "training_and_dev" / "dev_Q_A.json"
    documents_path = data_root / "training_and_dev" / "training_dev_technotes.json"
    smoke_path = data_root / "validation" / "validation_reference.json"
    smoke_documents_path = data_root / "validation" / "validation_technotes.json"
    audit_manifest = load_json(args.audit_manifest)
    train = load_json(train_path)
    dev = load_json(dev_path)
    smoke = load_json(smoke_path)
    documents = load_json(documents_path)
    smoke_documents = load_json(smoke_documents_path)
    documents, document_conflicts = merge_documents(documents, smoke_documents)
    if document_conflicts:
        raise ValueError(f"Found {document_conflicts} conflicting duplicate document IDs.")

    train_assignments = assign_train_splits(train, args.seed)
    train_fingerprints = {question_fingerprint(row) for row in train}
    near_dev_ids = near_duplicate_dev_ids(audit_manifest)

    canonical_rows = []
    for row in train:
        canonical_rows.append(
            canonical_question(
                row,
                "train",
                train_assignments[str(row["QUESTION_ID"])],
                train_fingerprints,
                near_dev_ids,
                documents,
            )
        )
    for row in dev:
        canonical_rows.append(
            canonical_question(
                row,
                "dev",
                "final_test",
                train_fingerprints,
                near_dev_ids,
                documents,
            )
        )
    for row in smoke:
        canonical_rows.append(
            canonical_question(
                row,
                "validation_smoke",
                "smoke_test",
                train_fingerprints,
                set(),
                documents,
            )
        )

    questions = pd.DataFrame(canonical_rows)
    questions["answer_start"] = pd.array(questions["answer_start"], dtype="Int64")
    questions["answer_end"] = pd.array(questions["answer_end"], dtype="Int64")
    question_groups_by_split = questions.groupby("research_split")["question_group_id"].apply(set)
    internal_names = ["fit", "calibration", "selection"]
    for left_index, left_name in enumerate(internal_names):
        for right_name in internal_names[left_index + 1 :]:
            overlap = question_groups_by_split[left_name] & question_groups_by_split[right_name]
            if overlap:
                raise RuntimeError(
                    f"Question groups cross {left_name}/{right_name}: {len(overlap)}"
                )

    output_dir.mkdir(parents=True)
    questions_path = output_dir / "questions.parquet"
    prepared_documents_path = output_dir / "documents.parquet"
    questions.to_parquet(questions_path, index=False, compression="zstd")
    referenced_document_ids = {
        document_id for candidates in questions["candidate_doc_ids"] for document_id in candidates
    }
    referenced_documents = {
        document_id: documents[document_id] for document_id in sorted(referenced_document_ids)
    }
    documents_frame = pd.DataFrame(document_records(referenced_documents))
    documents_frame.to_parquet(prepared_documents_path, index=False, compression="zstd")

    manifest = {
        "version": "techqa_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "split_method": "deterministic greedy 5-fold stratified group assignment; fold 0 calibration, fold 1 selection",
        "group_definition": "SHA-256 of casefolded, whitespace-normalized title + question text",
        "source_archive_sha256": audit_manifest["source"]["archive_sha256"],
        "raw_file_sha256": {
            "train": sha256_file(train_path),
            "dev": sha256_file(dev_path),
            "documents": sha256_file(documents_path),
            "validation_reference": sha256_file(smoke_path),
            "validation_documents": sha256_file(smoke_documents_path),
        },
        "split_summary": split_summary(questions),
        "official_dev_exact_duplicates_with_train": int(
            questions["exact_duplicate_with_official_train"].sum()
        ),
        "official_dev_near_duplicates_with_train": int(
            questions["near_duplicate_with_official_train"].sum()
        ),
        "deduplicated_candidate_lists": int(questions["candidates_deduplicated"].sum()),
        "documents": int(len(documents_frame)),
        "unreferenced_documents_excluded": int(len(documents) - len(documents_frame)),
        "outputs": {
            "questions": {
                "path": str(questions_path.relative_to(root)).replace("\\", "/"),
                "sha256": sha256_file(questions_path),
            },
            "documents": {
                "path": str(prepared_documents_path.relative_to(root)).replace("\\", "/"),
                "sha256": sha256_file(prepared_documents_path),
            },
        },
    }
    manifest_path = output_dir / "preparation_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    print(f"WROTE={output_dir}")
    print(json.dumps(manifest["split_summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
