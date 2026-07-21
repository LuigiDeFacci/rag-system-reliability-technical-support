"""Run the fixed document-level BM25 baseline without opening the final test gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from rag_confidence.data.audit import sha256_file
from rag_confidence.evaluation.retrieval_metrics import aggregate_retrieval_metrics
from rag_confidence.retrieval.bm25 import BM25Index


SAFE_DEFAULT_SPLITS = ("fit", "calibration", "selection")


def git_commit(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def enforce_test_gate(requested_splits: tuple[str, ...], allow_test: bool, gate_path: Path) -> None:
    if "final_test" not in requested_splits:
        return
    if not allow_test:
        raise PermissionError("final_test requires the explicit --allow-test flag")
    gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
    requirements = gate.get("requirements") or {}
    if not gate.get("allow_test") or not all(
        value is True for key, value in requirements.items() if key.endswith("_frozen")
    ):
        raise PermissionError("configs/final_test.yaml is still locked")


def score_summary(scores: list[float]) -> dict[str, float]:
    mean = sum(scores) / len(scores)
    variance = sum((score - mean) ** 2 for score in scores) / len(scores)
    standard_deviation = math.sqrt(variance)
    margin = scores[0] - scores[1] if len(scores) > 1 else 0.0
    return {
        "top1_score_raw": scores[0],
        "score_mean_candidates": mean,
        "score_std_candidates": standard_deviation,
        "top1_zscore_candidates": (
            0.0 if standard_deviation == 0 else (scores[0] - mean) / standard_deviation
        ),
        "margin_top1_top2_raw": margin,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/techqa_v1"))
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
    root = Path.cwd().resolve()
    processed_dir = args.processed_dir.resolve()
    requested_splits = tuple(dict.fromkeys(args.splits))
    enforce_test_gate(requested_splits, args.allow_test, args.test_gate)

    questions_path = processed_dir / "questions.parquet"
    documents_path = processed_dir / "documents.parquet"
    preparation_manifest_path = processed_dir / "preparation_manifest.json"
    questions = pd.read_parquet(questions_path)
    questions = questions[questions["research_split"].isin(requested_splits)].copy()
    if questions.empty:
        raise ValueError(f"No questions found for requested splits: {requested_splits}")
    unknown = set(requested_splits) - set(questions["research_split"])
    if unknown:
        raise ValueError(f"Requested splits are absent from the processed data: {sorted(unknown)}")
    documents = pd.read_parquet(documents_path)

    started = datetime.now(timezone.utc)
    config = {
        "method": "bm25_document",
        "corpus_statistics": "all unique official candidate documents",
        "ranking_scope": "per-query official candidate set",
        "document_text": "title + newline + text",
        "tokenizer": "casefolded technical regex preserving dots, colons, slashes and hyphens",
        "k1": args.k1,
        "b": args.b,
        "k": sorted(set(args.k)),
        "splits": list(requested_splits),
    }
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    run_id = f"{started.strftime('%Y%m%d-%H%M%S')}_bm25-doc_{config_hash[:8]}"
    run_dir = args.output_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    index = BM25Index(
        (
            (str(row.document_id), f"{row.title}\n{row.text}")
            for row in documents.itertuples(index=False)
        ),
        k1=args.k1,
        b=args.b,
    )

    ranking_records = []
    evaluation_records = []
    for row in questions.itertuples(index=False):
        ranked = index.rank(str(row.query_text), list(row.candidate_doc_ids))
        ranked_ids = [item.document_id for item in ranked]
        scores = [float(item.score) for item in ranked]
        summary = score_summary(scores)
        ranking_records.append(
            {
                "query_id": str(row.query_id),
                "research_split": str(row.research_split),
                "candidate_count": len(ranked),
                "ranked_document_ids": ranked_ids,
                "ranked_scores": scores,
                **summary,
            }
        )
        gold_rank = None
        if bool(row.answerable):
            try:
                gold_rank = ranked_ids.index(str(row.gold_document_id)) + 1
            except ValueError:
                gold_rank = None
        evaluation_record = {
            "query_id": str(row.query_id),
            "research_split": str(row.research_split),
            "answerable": bool(row.answerable),
            "gold_rank": gold_rank,
        }
        for cutoff in config["k"]:
            evaluation_record[f"evidence_at_{cutoff}"] = bool(
                gold_rank is not None and gold_rank <= cutoff
            )
        evaluation_records.append(evaluation_record)

    rankings = pd.DataFrame(ranking_records)
    evaluations = pd.DataFrame(evaluation_records)
    metrics: dict[str, Any] = {}
    for split in requested_splits:
        split_evaluation = evaluations[evaluations["research_split"] == split]
        answerable_ranks = [
            None if pd.isna(value) else int(value)
            for value in split_evaluation.loc[split_evaluation["answerable"], "gold_rank"]
        ]
        split_metrics = aggregate_retrieval_metrics(answerable_ranks, config["k"])
        split_metrics["all_queries"] = int(len(split_evaluation))
        for cutoff in config["k"]:
            split_metrics[f"evidence_positive_rate_at_{cutoff}"] = float(
                split_evaluation[f"evidence_at_{cutoff}"].mean()
            )
        metrics[split] = split_metrics

    rankings_path = run_dir / "rankings.parquet"
    evaluations_path = run_dir / "evaluation.parquet"
    metrics_path = run_dir / "metrics.json"
    config_path = run_dir / "config.json"
    rankings.to_parquet(rankings_path, index=False, compression="zstd")
    evaluations.to_parquet(evaluations_path, index=False, compression="zstd")
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    preparation_manifest = json.loads(preparation_manifest_path.read_text(encoding="utf-8"))
    manifest = {
        "run_id": run_id,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(root),
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "config_sha256": config_hash,
        "processed_data": preparation_manifest["outputs"],
        "final_test_used": "final_test" in requested_splits,
        "artifacts": {
            "rankings": sha256_file(rankings_path),
            "evaluation": sha256_file(evaluations_path),
            "metrics": sha256_file(metrics_path),
            "config": sha256_file(config_path),
        },
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"RUN_ID={run_id}")
    print(f"RUN_DIR={run_dir}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
