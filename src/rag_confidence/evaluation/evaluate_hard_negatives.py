"""Apply the frozen internal model to gold-removed hybrid stress contexts."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from rag_confidence.data.audit import sha256_file
from rag_confidence.features.build import (
    CODE_PATTERN,
    VERSION_PATTERN,
    concordance_features,
    score_distribution_features,
)
from rag_confidence.retrieval.bm25 import technical_tokenize
from rag_confidence.retrieval.run_bm25 import git_commit
from rag_confidence.scenarios.build_hard_negatives import (
    filter_gold_ranking,
    fuse_filtered_rankings,
)


def summarize_negative_probabilities(
    frame: pd.DataFrame, thresholds: dict[str, float]
) -> dict[str, Any]:
    if frame.empty:
        raise ValueError("Cannot summarize an empty stress set")
    probability = frame["probability"].to_numpy(dtype=np.float64)
    return {
        "rows": int(len(frame)),
        "mean_probability": float(probability.mean()),
        "median_probability": float(np.median(probability)),
        "probability_q90": float(np.quantile(probability, 0.9)),
        "brier_all_negative": float(np.mean(probability**2)),
        "false_acceptance_rate": {
            name: float((probability >= threshold).mean()) for name, threshold in thresholds.items()
        },
    }


def bootstrap_stress_intervals(
    comparison: pd.DataFrame,
    thresholds: dict[str, float],
    *,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    """Bootstrap paired rows; each row is one query in this stress set."""
    if comparison["query_id"].duplicated().any():
        raise ValueError("Stress bootstrap expects one paired row per query")
    generator = np.random.default_rng(seed)
    n_rows = len(comparison)
    samples = generator.integers(0, n_rows, size=(replicates, n_rows))
    stress_probability = comparison["probability"].to_numpy(dtype=np.float64)
    changes = comparison["probability_change_after_gold_removal"].to_numpy(dtype=np.float64)

    def interval(values: np.ndarray) -> dict[str, float]:
        return {
            "ci_lower": float(np.quantile(values, 0.025)),
            "ci_upper": float(np.quantile(values, 0.975)),
        }

    false_acceptance = {
        name: interval((stress_probability[samples] >= threshold).mean(axis=1))
        for name, threshold in thresholds.items()
    }
    return {
        "replicates": replicates,
        "seed": seed,
        "grouped_by": "query_id",
        "false_acceptance_rate": false_acceptance,
        "mean_probability_change": interval(changes[samples].mean(axis=1)),
    }


def feature_row(
    query_id: str,
    query_text: str,
    lexical: pd.Series,
    semantic: pd.Series,
    hybrid: pd.Series,
    cutoff: int,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "query_id": query_id,
        "query_length_chars": len(query_text),
        "query_length_technical_tokens": len(technical_tokenize(query_text)),
        "query_version_pattern_count": len(VERSION_PATTERN.findall(query_text)),
        "query_code_pattern_count": len(CODE_PATTERN.findall(query_text)),
    }
    for prefix, ranking in (("bm25", lexical), ("semantic", semantic), ("rrf", hybrid)):
        row.update(
            score_distribution_features(
                prefix,
                [float(value) for value in ranking["ranked_chunk_scores"]],
                [str(value) for value in ranking["ranked_chunk_document_ids"]],
                cutoff,
            )
        )
    row.update(concordance_features(lexical, semantic, hybrid, cutoff))
    return row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios-dir", type=Path, required=True)
    parser.add_argument("--bm25-run", type=Path, required=True)
    parser.add_argument("--semantic-run", type=Path, required=True)
    parser.add_argument("--confidence-run", type=Path, required=True)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/techqa_v1"))
    parser.add_argument("--output-root", type=Path, default=Path("results/runs"))
    parser.add_argument("--k", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scenarios_dir = args.scenarios_dir.resolve()
    scenario_manifest_path = scenarios_dir / "manifest.json"
    scenario_manifest = json.loads(scenario_manifest_path.read_text(encoding="utf-8"))
    if scenario_manifest["final_test_used"] or scenario_manifest["scope"] != "internal_only":
        raise PermissionError("Hard-negative evaluation accepts internal-only scenarios")
    if int(scenario_manifest["context_k"]) != args.k:
        raise ValueError("Requested k differs from the scenario manifest")
    scenarios_path = scenarios_dir / "scenarios.parquet"
    scenarios = pd.read_parquet(scenarios_path)
    stress = scenarios[
        (scenarios["research_split"] == "selection")
        & scenarios["scenario_id"].str.contains("__hard_hybrid_")
    ].copy()
    if stress["query_id"].duplicated().any():
        raise ValueError("Expected one hybrid stress scenario per selection query")

    confidence_run = args.confidence_run.resolve()
    confidence_manifest_path = confidence_run / "manifest.json"
    confidence_manifest = json.loads(confidence_manifest_path.read_text(encoding="utf-8"))
    if confidence_manifest["final_test_used"]:
        raise PermissionError("Hard-negative evaluation refuses final-test models")
    model_path = confidence_run / "models" / f"confidence_k{args.k}.joblib"
    model_bundle = joblib.load(model_path)
    if model_bundle["selected_calibrator"] != "raw":
        raise ValueError("This stress evaluator expects the selected raw model")

    processed_dir = args.processed_dir.resolve()
    questions_path = processed_dir / "questions.parquet"
    questions = pd.read_parquet(questions_path).set_index("query_id")
    run_paths = {"bm25": args.bm25_run.resolve(), "semantic": args.semantic_run.resolve()}
    run_manifests = {
        name: json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        for name, path in run_paths.items()
    }
    if any(manifest["final_test_used"] for manifest in run_manifests.values()):
        raise PermissionError("Hard-negative evaluation refuses final-test rankings")
    rankings = {
        name: pd.read_parquet(path / "rankings.parquet").set_index("query_id")
        for name, path in run_paths.items()
    }

    rows = []
    for scenario in stress.itertuples(index=False):
        query_id = str(scenario.query_id)
        gold_document_id = str(scenario.relevant_document_id)
        lexical = filter_gold_ranking(rankings["bm25"].loc[query_id], gold_document_id)
        semantic = filter_gold_ranking(rankings["semantic"].loc[query_id], gold_document_id)
        hybrid = fuse_filtered_rankings(lexical, semantic)
        row = feature_row(
            query_id,
            str(questions.loc[query_id, "query_text"]),
            lexical,
            semantic,
            hybrid,
            args.k,
        )
        row.update(
            {
                "scenario_id": str(scenario.scenario_id),
                "scenario_type": str(scenario.scenario_type),
                "evidence_sufficient": False,
            }
        )
        rows.append(row)
    stress_features = pd.DataFrame(rows)
    feature_columns = list(model_bundle["feature_columns"])
    probability = model_bundle["pipeline"].predict_proba(
        stress_features[feature_columns].astype(float)
    )[:, 1]
    predictions = stress_features[
        ["scenario_id", "query_id", "scenario_type", "evidence_sufficient"]
    ].copy()
    predictions["probability"] = probability

    selected_config = json.loads((confidence_run / "config.json").read_text(encoding="utf-8"))
    thresholds = {}
    confidence_metrics = json.loads((confidence_run / "metrics.json").read_text(encoding="utf-8"))[
        f"k{args.k}"
    ]["calibration_methods"]["raw"]["policies"]
    for name, values in confidence_metrics.items():
        thresholds[name] = float(values["threshold"])
    natural_predictions = pd.read_parquet(confidence_run / "selection_predictions.parquet")
    natural = natural_predictions[
        (natural_predictions["context_k"] == args.k)
        & (natural_predictions["method"] == "raw")
        & natural_predictions["query_id"].isin(predictions["query_id"])
    ][["query_id", "probability"]].rename(columns={"probability": "natural_probability"})
    comparison = predictions.merge(natural, on="query_id", validate="one_to_one")
    comparison["probability_change_after_gold_removal"] = (
        comparison["probability"] - comparison["natural_probability"]
    )
    metrics = {
        "scope": "selection_answerable_queries_constructed_stress",
        "prevalence": 0.0,
        "thresholds_frozen_on_natural_selection": thresholds,
        "overall": summarize_negative_probabilities(predictions, thresholds),
        "by_scenario_type": {
            str(name): summarize_negative_probabilities(group, thresholds)
            for name, group in predictions.groupby("scenario_type", sort=True)
        },
        "paired_probability_change": {
            "rows": int(len(comparison)),
            "mean_natural_probability": float(comparison["natural_probability"].mean()),
            "mean_stress_probability": float(comparison["probability"].mean()),
            "mean_change": float(comparison["probability_change_after_gold_removal"].mean()),
            "fraction_decreased": float(
                (comparison["probability_change_after_gold_removal"] < 0).mean()
            ),
        },
        "bootstrap": bootstrap_stress_intervals(comparison, thresholds, replicates=2000, seed=42),
        "interpretation_limit": (
            "all-negative artificial prevalence; false-acceptance stress only, not calibration"
        ),
    }

    started = datetime.now(timezone.utc)
    config = {
        "method": "frozen_logistic_on_gold_removed_hybrid_context",
        "context_k": args.k,
        "source_confidence_run_id": confidence_manifest["run_id"],
        "selected_calibrator": model_bundle["selected_calibrator"],
        "thresholds": thresholds,
        "feature_columns": feature_columns,
        "scenario_version": scenario_manifest["version"],
        "bootstrap": {"replicates": 2000, "seed": 42, "grouped_by": "query_id"},
        "base_model_config": selected_config,
    }
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    run_id = f"{started.strftime('%Y%m%d-%H%M%S')}_hard-stress-k{args.k}_{config_hash[:8]}"
    run_dir = args.output_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    paths = {
        "predictions": run_dir / "predictions.parquet",
        "comparison": run_dir / "paired_natural_comparison.parquet",
        "metrics": run_dir / "metrics.json",
        "config": run_dir / "config.json",
    }
    predictions.to_parquet(paths["predictions"], index=False, compression="zstd")
    comparison.to_parquet(paths["comparison"], index=False, compression="zstd")
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
        "sources": {
            "scenario_manifest": sha256_file(scenario_manifest_path),
            "scenarios": sha256_file(scenarios_path),
            "confidence_manifest": sha256_file(confidence_manifest_path),
            "model": sha256_file(model_path),
            "questions": sha256_file(questions_path),
            **{
                f"{name}_rankings": sha256_file(path / "rankings.parquet")
                for name, path in run_paths.items()
            },
        },
        "final_test_used": False,
        "artifacts": {name: sha256_file(path) for name, path in paths.items()},
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"RUN_ID={run_id}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
