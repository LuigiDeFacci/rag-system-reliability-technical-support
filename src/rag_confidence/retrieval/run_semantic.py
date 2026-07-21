"""Run pinned semantic retrieval on internal splits or through the final-test gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sentence_transformers
import torch
import yaml
from sentence_transformers import SentenceTransformer

from rag_confidence.data.audit import sha256_file
from rag_confidence.evaluation.retrieval_metrics import aggregate_retrieval_metrics
from rag_confidence.retrieval.build_embeddings import select_device
from rag_confidence.retrieval.run_bm25 import (
    SAFE_DEFAULT_SPLITS,
    enforce_test_gate,
    git_commit,
    score_summary,
)
from rag_confidence.retrieval.semantic import interval_union_covers, rank_candidate_chunks
from rag_confidence.runtime import configure_system_trust_store


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/techqa_v1"))
    parser.add_argument(
        "--embeddings-dir", type=Path, default=Path("data/interim/embeddings_bge_v1")
    )
    parser.add_argument("--config", type=Path, default=Path("configs/retrieval.yaml"))
    parser.add_argument("--model-cache", type=Path, default=Path("data/interim/model_cache"))
    parser.add_argument("--output-root", type=Path, default=Path("results/runs"))
    parser.add_argument("--splits", nargs="+", default=list(SAFE_DEFAULT_SPLITS))
    parser.add_argument("--k", nargs="+", type=int, default=[1, 3, 5, 10])
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--allow-test", action="store_true")
    parser.add_argument("--test-gate", type=Path, default=Path("configs/final_test.yaml"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_system_trust_store()
    requested_splits = tuple(dict.fromkeys(args.splits))
    enforce_test_gate(requested_splits, args.allow_test, args.test_gate)
    cutoffs = sorted(set(args.k))
    if not cutoffs or cutoffs[0] <= 0:
        raise ValueError("All k values must be positive")

    processed_dir = args.processed_dir.resolve()
    questions_path = processed_dir / "questions.parquet"
    questions = pd.read_parquet(questions_path)
    questions = questions[questions["research_split"].isin(requested_splits)].copy()
    unknown = set(requested_splits) - set(questions["research_split"])
    if questions.empty or unknown:
        raise ValueError(f"Missing requested splits: {sorted(unknown)}")

    embeddings_dir = args.embeddings_dir.resolve()
    embeddings_path = embeddings_dir / "chunk_embeddings.npy"
    index_path = embeddings_dir / "chunk_index.parquet"
    embedding_manifest_path = embeddings_dir / "manifest.json"
    embeddings = np.load(embeddings_path, mmap_mode="r", allow_pickle=False)
    index = pd.read_parquet(index_path)
    if len(index) != len(embeddings):
        raise ValueError("Chunk index and embeddings have different row counts")
    chunk_records = index.to_dict("records")
    rows_by_document: defaultdict[str, list[int]] = defaultdict(list)
    for row_index, document_id in enumerate(index["document_id"].astype(str)):
        rows_by_document[document_id].append(row_index)

    retrieval_config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    semantic = retrieval_config["semantic"]
    device = select_device(args.device)
    model = SentenceTransformer(
        semantic["model"],
        revision=semantic["revision"],
        cache_folder=str(args.model_cache.resolve()),
        device=device,
        local_files_only=True,
    )
    query_inputs = [semantic["query_prefix"] + str(value) for value in questions["query_text"]]
    query_embeddings = model.encode(
        query_inputs,
        batch_size=args.batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=bool(semantic["normalize_embeddings"]),
    ).astype(np.float32, copy=False)

    started = datetime.now(timezone.utc)
    config = {
        "method": "semantic_chunk_exact",
        "model": semantic["model"],
        "revision": semantic["revision"],
        "query_prefix": semantic["query_prefix"],
        "passage_prefix": semantic["passage_prefix"],
        "normalize_embeddings": bool(semantic["normalize_embeddings"]),
        "ranking_scope": "all chunks of each query's official candidate documents",
        "document_aggregation": "maximum chunk cosine",
        "k": cutoffs,
        "splits": list(requested_splits),
        "device": device,
        "batch_size": args.batch_size,
    }
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    run_id = f"{started.strftime('%Y%m%d-%H%M%S')}_semantic-chunk_{config_hash[:8]}"
    run_dir = args.output_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    ranking_records = []
    evaluation_records = []
    for query_position, row in enumerate(questions.itertuples(index=False)):
        candidate_ids = [str(value) for value in row.candidate_doc_ids]
        missing = [
            document_id for document_id in candidate_ids if document_id not in rows_by_document
        ]
        if missing:
            raise KeyError(f"Candidate documents missing chunks: {missing[:5]}")
        ranked_chunks, ranked_documents = rank_candidate_chunks(
            query_embeddings[query_position],
            embeddings,
            chunk_records,
            rows_by_document,
            candidate_ids,
        )
        chunk_scores = [item.score for item in ranked_chunks]
        summary = {f"semantic_{key}": value for key, value in score_summary(chunk_scores).items()}
        ranking_records.append(
            {
                "query_id": str(row.query_id),
                "research_split": str(row.research_split),
                "candidate_document_count": len(candidate_ids),
                "candidate_chunk_count": len(ranked_chunks),
                "ranked_chunk_ids": [item.chunk_id for item in ranked_chunks],
                "ranked_chunk_document_ids": [item.document_id for item in ranked_chunks],
                "ranked_chunk_scores": chunk_scores,
                "ranked_chunk_body_starts": [item.body_start_char for item in ranked_chunks],
                "ranked_chunk_body_ends": [item.body_end_char for item in ranked_chunks],
                "ranked_document_ids": [item.document_id for item in ranked_documents],
                "ranked_document_scores": [item.score for item in ranked_documents],
                "ranked_document_best_chunks": [item.best_chunk_id for item in ranked_documents],
                **summary,
            }
        )

        answerable = bool(row.answerable)
        gold_document_id = str(row.gold_document_id) if answerable else None
        answer_start = int(row.answer_start) if answerable else None
        answer_end = int(row.answer_end) if answerable else None
        document_rank = None
        containing_chunk_rank = None
        if answerable:
            document_ids = [item.document_id for item in ranked_documents]
            document_rank = document_ids.index(gold_document_id) + 1
            containing_chunk_rank = next(
                (
                    rank
                    for rank, item in enumerate(ranked_chunks, start=1)
                    if item.document_id == gold_document_id
                    and item.body_start_char <= answer_start
                    and answer_end <= item.body_end_char
                ),
                None,
            )
        evaluation: dict[str, Any] = {
            "query_id": str(row.query_id),
            "research_split": str(row.research_split),
            "answerable": answerable,
            "gold_document_id": gold_document_id,
            "gold_document_rank": document_rank,
            "first_containing_chunk_rank": containing_chunk_rank,
        }
        for cutoff in cutoffs:
            selected_gold_intervals = [
                (item.body_start_char, item.body_end_char)
                for item in ranked_chunks[:cutoff]
                if answerable and item.document_id == gold_document_id
            ]
            evaluation[f"evidence_at_{cutoff}"] = bool(
                answerable
                and interval_union_covers(selected_gold_intervals, answer_start, answer_end)
            )
            evaluation[f"gold_document_at_{cutoff}"] = bool(
                document_rank is not None and document_rank <= cutoff
            )
        evaluation_records.append(evaluation)

    rankings = pd.DataFrame(ranking_records)
    evaluations = pd.DataFrame(evaluation_records)
    metrics: dict[str, Any] = {}
    for split in requested_splits:
        split_frame = evaluations[evaluations["research_split"] == split]
        answerable_frame = split_frame[split_frame["answerable"]]
        containing_ranks = [
            None if pd.isna(value) else int(value)
            for value in answerable_frame["first_containing_chunk_rank"]
        ]
        document_ranks = [int(value) for value in answerable_frame["gold_document_rank"]]
        split_metrics: dict[str, Any] = {
            "all_queries": int(len(split_frame)),
            "containing_chunk": aggregate_retrieval_metrics(containing_ranks, cutoffs),
            "document_proxy": aggregate_retrieval_metrics(document_ranks, cutoffs),
        }
        for cutoff in cutoffs:
            split_metrics[f"context_evidence_positive_rate_at_{cutoff}"] = float(
                split_frame[f"evidence_at_{cutoff}"].mean()
            )
            split_metrics[f"answerable_context_recall_at_{cutoff}"] = float(
                answerable_frame[f"evidence_at_{cutoff}"].mean()
            )
        metrics[split] = split_metrics

    paths = {
        "rankings": run_dir / "rankings.parquet",
        "evaluation": run_dir / "evaluation.parquet",
        "metrics": run_dir / "metrics.json",
        "config": run_dir / "config.json",
    }
    rankings.to_parquet(paths["rankings"], index=False, compression="zstd")
    evaluations.to_parquet(paths["evaluation"], index=False, compression="zstd")
    paths["metrics"].write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["config"].write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    embedding_manifest = json.loads(embedding_manifest_path.read_text(encoding="utf-8"))
    manifest = {
        "run_id": run_id,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(Path.cwd().resolve()),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "sentence_transformers": sentence_transformers.__version__,
        "config_sha256": config_hash,
        "questions_sha256": sha256_file(questions_path),
        "embedding_manifest": embedding_manifest,
        "final_test_used": "final_test" in requested_splits,
        "artifacts": {name: sha256_file(path) for name, path in paths.items()},
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"RUN_ID={run_id}")
    print(f"RUN_DIR={run_dir}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
