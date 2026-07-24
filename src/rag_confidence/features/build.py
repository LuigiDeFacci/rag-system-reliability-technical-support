"""Extract production-available retrieval features into a label-free table.

Gold documents, answer spans and scenario labels are excluded by explicit
forbidden-column checks, so the no-leakage rule is executable.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from rag_confidence.data.audit import sha256_file
from rag_confidence.retrieval.bm25 import technical_tokenize
from rag_confidence.retrieval.run_bm25 import git_commit


VERSION_PATTERN = re.compile(r"(?i)\b(?:v(?:ersion)?\s*)?\d+(?:\.\d+){1,4}\b")
CODE_PATTERN = re.compile(r"(?i)\b(?:CVE-\d{4}-\d+|[A-Z]{2,}[-_]?[A-Z]*\d{2,})\b")
FORBIDDEN_FEATURE_FRAGMENTS = (
    "gold",
    "answerable",
    "evidence_sufficient",
    "scenario_type",
    "relevant_document",
)


def score_distribution_features(
    prefix: str,
    scores: list[float],
    document_ids: list[str],
    cutoff: int,
) -> dict[str, float]:
    """Summarize one retriever's score distribution at a requested cutoff."""
    values = np.asarray(scores, dtype=np.float64)
    if len(values) < cutoff or len(values) < 2:
        raise ValueError("Ranking is shorter than the requested cutoff")
    candidate_mean = float(values.mean())
    candidate_std = float(values.std())
    zscores = (
        np.zeros_like(values) if candidate_std == 0 else (values - candidate_mean) / candidate_std
    )
    top = values[:cutoff]
    top_z = zscores[:cutoff]
    return {
        f"{prefix}_top1_score_raw": float(values[0]),
        f"{prefix}_margin_top1_top2_raw": float(values[0] - values[1]),
        f"{prefix}_topk_mean_raw": float(top.mean()),
        f"{prefix}_topk_std_raw": float(top.std()),
        f"{prefix}_topk_range_raw": float(top.max() - top.min()),
        f"{prefix}_candidate_mean_raw": candidate_mean,
        f"{prefix}_candidate_std_raw": candidate_std,
        f"{prefix}_top1_zscore": float(zscores[0]),
        f"{prefix}_topk_mean_zscore": float(top_z.mean()),
        f"{prefix}_topk_std_zscore": float(top_z.std()),
        f"{prefix}_topk_unique_document_ratio": len(set(document_ids[:cutoff])) / cutoff,
    }


def jaccard(left: list[str], right: list[str]) -> float:
    left_set, right_set = set(left), set(right)
    union = left_set | right_set
    return 1.0 if not union else len(left_set & right_set) / len(union)


def rank_correlation(left: list[str], right: list[str]) -> float:
    if set(left) != set(right):
        raise ValueError("Rank correlation requires identical item universes")
    left_rank = {item: rank for rank, item in enumerate(left)}
    x = np.asarray([left_rank[item] for item in right], dtype=np.float64)
    y = np.arange(len(right), dtype=np.float64)
    correlation = float(np.corrcoef(x, y)[0, 1])
    return 0.0 if not math.isfinite(correlation) else correlation


def concordance_features(
    lexical: pd.Series, semantic: pd.Series, hybrid: pd.Series, cutoff: int
) -> dict[str, float | bool]:
    lex_chunks = [str(value) for value in lexical["ranked_chunk_ids"]]
    sem_chunks = [str(value) for value in semantic["ranked_chunk_ids"]]
    hybrid_chunks = [str(value) for value in hybrid["ranked_chunk_ids"]]
    lex_docs = [str(value) for value in lexical["ranked_chunk_document_ids"]]
    sem_docs = [str(value) for value in semantic["ranked_chunk_document_ids"]]
    hybrid_docs = [str(value) for value in hybrid["ranked_chunk_document_ids"]]
    return {
        "lex_sem_top1_chunk_agreement": lex_chunks[0] == sem_chunks[0],
        "lex_sem_top1_document_agreement": lex_docs[0] == sem_docs[0],
        "lex_sem_topk_chunk_jaccard": jaccard(lex_chunks[:cutoff], sem_chunks[:cutoff]),
        "lex_sem_topk_document_jaccard": jaccard(lex_docs[:cutoff], sem_docs[:cutoff]),
        "hybrid_lex_topk_chunk_jaccard": jaccard(hybrid_chunks[:cutoff], lex_chunks[:cutoff]),
        "hybrid_sem_topk_chunk_jaccard": jaccard(hybrid_chunks[:cutoff], sem_chunks[:cutoff]),
        "lex_sem_full_rank_correlation": rank_correlation(lex_chunks, sem_chunks),
        "hybrid_context_unique_documents": float(len(set(hybrid_docs[:cutoff]))),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios-dir", type=Path, required=True)
    parser.add_argument("--bm25-run", type=Path, required=True)
    parser.add_argument("--semantic-run", type=Path, required=True)
    parser.add_argument("--hybrid-run", type=Path, required=True)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/techqa_v1"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/interim/features_natural_v1"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite features: {output_dir}")

    scenarios_path = args.scenarios_dir.resolve() / "scenarios.parquet"
    scenarios_manifest_path = args.scenarios_dir.resolve() / "manifest.json"
    scenarios = pd.read_parquet(scenarios_path)
    questions_path = args.processed_dir.resolve() / "questions.parquet"
    questions = pd.read_parquet(questions_path).set_index("query_id")
    run_paths = {
        "bm25": args.bm25_run.resolve(),
        "semantic": args.semantic_run.resolve(),
        "rrf": args.hybrid_run.resolve(),
    }
    rankings = {
        name: pd.read_parquet(path / "rankings.parquet").set_index("query_id")
        for name, path in run_paths.items()
    }
    run_manifests = {
        name: json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        for name, path in run_paths.items()
    }
    # Features are created before the final gate; this guard prevents accidental
    # reuse of a retrieval run that already touched the holdout.
    if any(manifest["final_test_used"] for manifest in run_manifests.values()):
        raise PermissionError("Feature extraction refuses final-test source runs")

    feature_rows = []
    label_rows = []
    for scenario in scenarios.itertuples(index=False):
        query_id = str(scenario.query_id)
        cutoff = int(scenario.context_k)
        question = questions.loc[query_id]
        lexical = rankings["bm25"].loc[query_id]
        semantic = rankings["semantic"].loc[query_id]
        hybrid = rankings["rrf"].loc[query_id]
        row: dict[str, Any] = {
            "scenario_id": str(scenario.scenario_id),
            "query_id": query_id,
            "research_split": str(scenario.research_split),
            "context_k": cutoff,
            "query_length_chars": len(str(question["query_text"])),
            "query_length_technical_tokens": len(technical_tokenize(str(question["query_text"]))),
            "query_version_pattern_count": len(
                VERSION_PATTERN.findall(str(question["query_text"]))
            ),
            "query_code_pattern_count": len(CODE_PATTERN.findall(str(question["query_text"]))),
        }
        for prefix, ranking in (
            ("bm25", lexical),
            ("semantic", semantic),
            ("rrf", hybrid),
        ):
            row.update(
                score_distribution_features(
                    prefix,
                    [float(value) for value in ranking["ranked_chunk_scores"]],
                    [str(value) for value in ranking["ranked_chunk_document_ids"]],
                    cutoff,
                )
            )
        row.update(concordance_features(lexical, semantic, hybrid, cutoff))
        feature_rows.append(row)
        label_rows.append(
            {
                "scenario_id": str(scenario.scenario_id),
                "query_id": query_id,
                "research_split": str(scenario.research_split),
                "context_k": cutoff,
                "evidence_sufficient": bool(scenario.evidence_sufficient),
                "scenario_type": str(scenario.scenario_type),
            }
        )

    features = pd.DataFrame(feature_rows)
    labels = pd.DataFrame(label_rows)
    if features.isna().any().any():
        raise ValueError("Feature table contains missing values")
    numeric = features.drop(columns=["scenario_id", "query_id", "research_split"]).select_dtypes(
        include=["number"]
    )
    if not np.isfinite(numeric.to_numpy(dtype=np.float64)).all():
        raise ValueError("Feature table contains non-finite numeric values")
    forbidden = [
        column
        for column in features.columns
        if any(fragment in column.casefold() for fragment in FORBIDDEN_FEATURE_FRAGMENTS)
    ]
    # Fail closed if a gold/label-like column reaches the production feature set.
    if forbidden:
        raise ValueError(f"Forbidden feature columns detected: {forbidden}")

    output_dir.mkdir(parents=True, exist_ok=False)
    features_path = output_dir / "features.parquet"
    labels_path = output_dir / "labels.parquet"
    features.to_parquet(features_path, index=False, compression="zstd")
    labels.to_parquet(labels_path, index=False, compression="zstd")
    identifier_columns = ["scenario_id", "query_id", "research_split", "context_k"]
    model_feature_columns = [
        column for column in features.columns if column not in identifier_columns
    ]
    schema = {
        "identifier_columns": identifier_columns,
        "model_feature_columns": model_feature_columns,
        "label_column": "evidence_sufficient",
        "evaluation_only_columns": ["scenario_type"],
        "feature_groups": {
            "lexical": [c for c in model_feature_columns if c.startswith("bm25_")],
            "semantic": [c for c in model_feature_columns if c.startswith("semantic_")],
            "hybrid": [c for c in model_feature_columns if c.startswith("rrf_")],
            "concordance": [
                c
                for c in model_feature_columns
                if "jaccard" in c or "agreement" in c or "rank_correlation" in c
            ],
            "query": [c for c in model_feature_columns if c.startswith("query_")],
            "context": [c for c in model_feature_columns if c.startswith("hybrid_context_")],
        },
    }
    schema_path = output_dir / "schema.json"
    schema_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    scenario_manifest = json.loads(scenarios_manifest_path.read_text(encoding="utf-8"))
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "version": "features_natural_v1",
        "code_commit": git_commit(Path.cwd().resolve()),
        "rows": int(len(features)),
        "unique_queries": int(features["query_id"].nunique()),
        "model_feature_count": len(model_feature_columns),
        "scenario_manifest": scenario_manifest,
        "source_runs": {
            name: {
                "run_id": run_manifests[name]["run_id"],
                "rankings_sha256": sha256_file(path / "rankings.parquet"),
            }
            for name, path in run_paths.items()
        },
        "artifacts": {
            "features": sha256_file(features_path),
            "labels": sha256_file(labels_path),
            "schema": sha256_file(schema_path),
        },
        "final_test_used": False,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
