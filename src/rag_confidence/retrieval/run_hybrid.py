"""Fuse aligned lexical and semantic chunk runs with RRF."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from rag_confidence.data.audit import sha256_file
from rag_confidence.evaluation.context_retrieval import evaluate_context_rankings
from rag_confidence.retrieval.rrf import reciprocal_rank_fusion
from rag_confidence.retrieval.run_bm25 import enforce_test_gate, git_commit, score_summary
from rag_confidence.retrieval.semantic import RankedChunk


def chunks_from_row(row: pd.Series) -> list[RankedChunk]:
    fields = zip(
        row["ranked_chunk_ids"],
        row["ranked_chunk_document_ids"],
        row["ranked_chunk_scores"],
        row["ranked_chunk_body_starts"],
        row["ranked_chunk_body_ends"],
        strict=True,
    )
    return [
        RankedChunk(
            row_index=rank,
            chunk_id=str(chunk_id),
            document_id=str(document_id),
            chunk_index=int(str(chunk_id).rsplit("::c", maxsplit=1)[1]),
            body_start_char=int(start),
            body_end_char=int(end),
            score=float(score),
        )
        for rank, (chunk_id, document_id, score, start, end) in enumerate(fields)
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bm25-run", type=Path, required=True)
    parser.add_argument("--semantic-run", type=Path, required=True)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/techqa_v1"))
    parser.add_argument("--output-root", type=Path, default=Path("results/runs"))
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--k", nargs="+", type=int, default=[1, 3, 5, 10])
    parser.add_argument("--allow-test", action="store_true")
    parser.add_argument("--test-gate", type=Path, default=Path("configs/final_test.yaml"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cutoffs = sorted(set(args.k))
    lexical_path = args.bm25_run.resolve() / "rankings.parquet"
    semantic_path = args.semantic_run.resolve() / "rankings.parquet"
    lexical = pd.read_parquet(lexical_path).set_index("query_id")
    semantic = pd.read_parquet(semantic_path).set_index("query_id")
    if set(lexical.index) != set(semantic.index):
        raise ValueError("Source runs contain different query IDs")
    if set(lexical["research_split"]) != set(semantic["research_split"]):
        raise ValueError("Source runs contain different research splits")
    requested_splits = tuple(dict.fromkeys(str(value) for value in lexical["research_split"]))
    enforce_test_gate(requested_splits, args.allow_test, args.test_gate)

    questions_path = args.processed_dir.resolve() / "questions.parquet"
    questions = pd.read_parquet(questions_path)
    questions = questions[questions["query_id"].isin(lexical.index)].copy()
    started = datetime.now(timezone.utc)
    config = {
        "method": "reciprocal_rank_fusion_chunks",
        "rrf_k": args.rrf_k,
        "k": cutoffs,
        "splits": list(requested_splits),
        "bm25_rankings_sha256": sha256_file(lexical_path),
        "semantic_rankings_sha256": sha256_file(semantic_path),
    }
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    run_id = f"{started.strftime('%Y%m%d-%H%M%S')}_hybrid-rrf_{config_hash[:8]}"
    run_dir = args.output_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    records = []
    for query_id in lexical.index:
        lexical_row = lexical.loc[query_id]
        semantic_row = semantic.loc[query_id]
        fused, documents = reciprocal_rank_fusion(
            chunks_from_row(lexical_row), chunks_from_row(semantic_row), rrf_k=args.rrf_k
        )
        scores = [item.score for item in fused]
        records.append(
            {
                "query_id": str(query_id),
                "research_split": str(lexical_row["research_split"]),
                "candidate_document_count": int(lexical_row["candidate_document_count"]),
                "candidate_chunk_count": len(fused),
                "ranked_chunk_ids": [item.chunk_id for item in fused],
                "ranked_chunk_document_ids": [item.document_id for item in fused],
                "ranked_chunk_scores": scores,
                "ranked_chunk_body_starts": [item.body_start_char for item in fused],
                "ranked_chunk_body_ends": [item.body_end_char for item in fused],
                "ranked_document_ids": [item.document_id for item in documents],
                "ranked_document_scores": [item.score for item in documents],
                "ranked_document_best_chunks": [item.best_chunk_id for item in documents],
                **{f"rrf_{key}": value for key, value in score_summary(scores).items()},
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
    manifest = {
        "run_id": run_id,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(Path.cwd().resolve()),
        "python": platform.python_version(),
        "config_sha256": config_hash,
        "questions_sha256": sha256_file(questions_path),
        "source_runs": {
            "bm25": json.loads((args.bm25_run.resolve() / "manifest.json").read_text()),
            "semantic": json.loads((args.semantic_run.resolve() / "manifest.json").read_text()),
        },
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
