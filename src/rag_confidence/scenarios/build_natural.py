"""Build natural hybrid-context sufficiency scenarios without artificial removals."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from rag_confidence.data.audit import sha256_file
from rag_confidence.retrieval.run_bm25 import git_commit


def unique_preserving_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def build_records(
    questions: pd.DataFrame,
    rankings: pd.DataFrame,
    evaluations: pd.DataFrame,
    cutoffs: list[int],
    source_run_id: str,
    code_commit: str | None,
    seed: int,
) -> list[dict[str, Any]]:
    ranking_by_query = rankings.set_index("query_id")
    evaluation_by_query = evaluations.set_index("query_id")
    if set(questions["query_id"]) != set(ranking_by_query.index):
        raise ValueError("Questions and rankings contain different query IDs")
    if set(questions["query_id"]) != set(evaluation_by_query.index):
        raise ValueError("Questions and evaluations contain different query IDs")

    records = []
    for question in questions.itertuples(index=False):
        query_id = str(question.query_id)
        ranking = ranking_by_query.loc[query_id]
        evaluation = evaluation_by_query.loc[query_id]
        for cutoff in cutoffs:
            included_chunks = [str(value) for value in ranking["ranked_chunk_ids"][:cutoff]]
            included_documents = unique_preserving_order(
                [str(value) for value in ranking["ranked_chunk_document_ids"][:cutoff]]
            )
            sufficient = bool(evaluation[f"evidence_at_{cutoff}"])
            if not bool(question.answerable):
                scenario_type = "native_unanswerable"
                reason = "no annotated evidence in the official candidate universe"
            elif sufficient:
                scenario_type = "natural_sufficient"
                reason = "top-k chunk union continuously covers the annotated span"
            else:
                scenario_type = "natural_retrieval_miss"
                reason = "top-k chunk union does not cover the annotated span"
            records.append(
                {
                    "scenario_id": f"{query_id}__hybrid_k{cutoff}",
                    "query_id": query_id,
                    "research_split": str(question.research_split),
                    "context_k": cutoff,
                    "scenario_family": "natural_hybrid_retrieval",
                    "scenario_type": scenario_type,
                    "evidence_sufficient": sufficient,
                    "relevant_document_id": (
                        str(question.gold_document_id) if bool(question.answerable) else None
                    ),
                    "removed_document_ids": [],
                    "included_document_ids": included_documents,
                    "included_chunk_ids": included_chunks,
                    "classification_reason": reason,
                    "conflicting_product": None,
                    "conflicting_version_or_code": None,
                    "negative_selection_method": (
                        "natural_hybrid_retrieval" if not sufficient else None
                    ),
                    "seed": seed,
                    "source_run_id": source_run_id,
                    "code_commit": code_commit,
                }
            )
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hybrid-run", type=Path, required=True)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/techqa_v1"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/interim/scenarios_natural_v1")
    )
    parser.add_argument("--k", nargs="+", type=int, default=[1, 3, 5, 10])
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite scenarios: {output_dir}")
    cutoffs = sorted(set(args.k))
    if not cutoffs or cutoffs[0] <= 0:
        raise ValueError("All k values must be positive")

    hybrid_run = args.hybrid_run.resolve()
    source_manifest = json.loads((hybrid_run / "manifest.json").read_text(encoding="utf-8"))
    if source_manifest["final_test_used"]:
        raise PermissionError("Natural scenario builder refuses final-test source runs")
    rankings_path = hybrid_run / "rankings.parquet"
    evaluations_path = hybrid_run / "evaluation.parquet"
    questions_path = args.processed_dir.resolve() / "questions.parquet"
    rankings = pd.read_parquet(rankings_path)
    evaluations = pd.read_parquet(evaluations_path)
    questions = pd.read_parquet(questions_path)
    questions = questions[questions["query_id"].isin(rankings["query_id"])].copy()
    commit = git_commit(Path.cwd().resolve())
    records = build_records(
        questions,
        rankings,
        evaluations,
        cutoffs,
        str(source_manifest["run_id"]),
        commit,
        args.seed,
    )
    scenarios = pd.DataFrame(records)
    output_dir.mkdir(parents=True, exist_ok=False)
    scenarios_path = output_dir / "scenarios.parquet"
    scenarios.to_parquet(scenarios_path, index=False, compression="zstd")

    prevalence = {}
    for (split, cutoff), frame in scenarios.groupby(["research_split", "context_k"], sort=True):
        prevalence[f"{split}__k{cutoff}"] = {
            "rows": int(len(frame)),
            "positive": int(frame["evidence_sufficient"].sum()),
            "negative": int((~frame["evidence_sufficient"]).sum()),
            "positive_rate": float(frame["evidence_sufficient"].mean()),
            "scenario_types": {
                str(key): int(value)
                for key, value in frame["scenario_type"].value_counts().sort_index().items()
            },
        }
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "version": "natural_scenarios_v1",
        "source_run_id": source_manifest["run_id"],
        "source_rankings_sha256": sha256_file(rankings_path),
        "source_evaluation_sha256": sha256_file(evaluations_path),
        "questions_sha256": sha256_file(questions_path),
        "code_commit": commit,
        "seed": args.seed,
        "cutoffs": cutoffs,
        "rows": int(len(scenarios)),
        "unique_queries": int(scenarios["query_id"].nunique()),
        "prevalence": prevalence,
        "scenarios_sha256": sha256_file(scenarios_path),
        "final_test_used": False,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
