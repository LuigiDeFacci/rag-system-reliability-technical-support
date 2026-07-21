"""Run BM25 over the same chunks used by the semantic retriever."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from rag_confidence.data.audit import sha256_file
from rag_confidence.evaluation.context_retrieval import evaluate_context_rankings
from rag_confidence.retrieval.chunk_bm25 import (
    ChunkBM25Statistics,
    rank_bm25_candidate_chunks,
)
from rag_confidence.retrieval.run_bm25 import (
    SAFE_DEFAULT_SPLITS,
    enforce_test_gate,
    git_commit,
    score_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/techqa_v1"))
    parser.add_argument("--chunks-dir", type=Path, default=Path("data/interim/chunks_bge_v1"))
    parser.add_argument("--output-root", type=Path, default=Path("results/runs"))
    parser.add_argument("--splits", nargs="+", default=list(SAFE_DEFAULT_SPLITS))
    parser.add_argument("--k", nargs="+", type=int, default=[1, 3, 5, 10])
    parser.add_argument("--k1", type=float, default=1.2)
    parser.add_argument("--b", type=float, default=0.75)
    parser.add_argument("--allow-test", action="store_true")
    parser.add_argument("--test-gate", type=Path, default=Path("configs/final_test.yaml"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    requested_splits = tuple(dict.fromkeys(args.splits))
    enforce_test_gate(requested_splits, args.allow_test, args.test_gate)
    cutoffs = sorted(set(args.k))
    if not cutoffs or cutoffs[0] <= 0:
        raise ValueError("All k values must be positive")

    questions_path = args.processed_dir.resolve() / "questions.parquet"
    questions = pd.read_parquet(questions_path)
    questions = questions[questions["research_split"].isin(requested_splits)].copy()
    unknown = set(requested_splits) - set(questions["research_split"])
    if questions.empty or unknown:
        raise ValueError(f"Missing requested splits: {sorted(unknown)}")

    chunks_path = args.chunks_dir.resolve() / "chunks.parquet"
    chunks_manifest_path = args.chunks_dir.resolve() / "manifest.json"
    chunks = pd.read_parquet(chunks_path)
    passage_texts = chunks["passage_text"].astype(str).tolist()
    chunk_records = chunks.drop(columns=["passage_text"]).to_dict("records")
    rows_by_document: defaultdict[str, list[int]] = defaultdict(list)
    for row_index, document_id in enumerate(chunks["document_id"].astype(str)):
        rows_by_document[document_id].append(row_index)

    started = datetime.now(timezone.utc)
    statistics = ChunkBM25Statistics(passage_texts, k1=args.k1, b=args.b)
    config = {
        "method": "bm25_chunk",
        "corpus_statistics": "all chunks from unique official candidate documents",
        "ranking_scope": "all chunks of each query's official candidate documents",
        "document_aggregation": "maximum chunk BM25",
        "tokenizer": "casefolded technical regex preserving dots, colons, slashes and hyphens",
        "k1": args.k1,
        "b": args.b,
        "k": cutoffs,
        "splits": list(requested_splits),
    }
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    run_id = f"{started.strftime('%Y%m%d-%H%M%S')}_bm25-chunk_{config_hash[:8]}"
    run_dir = args.output_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    records = []
    for row in questions.itertuples(index=False):
        candidate_ids = [str(value) for value in row.candidate_doc_ids]
        missing = [
            document_id for document_id in candidate_ids if document_id not in rows_by_document
        ]
        if missing:
            raise KeyError(f"Candidate documents missing chunks: {missing[:5]}")
        ranked_chunks, ranked_documents = rank_bm25_candidate_chunks(
            str(row.query_text),
            passage_texts,
            chunk_records,
            rows_by_document,
            candidate_ids,
            statistics,
        )
        scores = [item.score for item in ranked_chunks]
        records.append(
            {
                "query_id": str(row.query_id),
                "research_split": str(row.research_split),
                "candidate_document_count": len(candidate_ids),
                "candidate_chunk_count": len(ranked_chunks),
                "ranked_chunk_ids": [item.chunk_id for item in ranked_chunks],
                "ranked_chunk_document_ids": [item.document_id for item in ranked_chunks],
                "ranked_chunk_scores": scores,
                "ranked_chunk_body_starts": [item.body_start_char for item in ranked_chunks],
                "ranked_chunk_body_ends": [item.body_end_char for item in ranked_chunks],
                "ranked_document_ids": [item.document_id for item in ranked_documents],
                "ranked_document_scores": [item.score for item in ranked_documents],
                "ranked_document_best_chunks": [item.best_chunk_id for item in ranked_documents],
                **{f"bm25_{key}": value for key, value in score_summary(scores).items()},
            }
        )

    rankings = pd.DataFrame(records)
    evaluations, metrics = evaluate_context_rankings(questions, rankings, cutoffs)
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
    chunk_manifest = json.loads(chunks_manifest_path.read_text(encoding="utf-8"))
    manifest = {
        "run_id": run_id,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(Path.cwd().resolve()),
        "python": platform.python_version(),
        "config_sha256": config_hash,
        "questions_sha256": sha256_file(questions_path),
        "chunk_manifest": chunk_manifest,
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
