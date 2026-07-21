"""Run paired grouped bootstrap and simple feature-group ablations on selection."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import sklearn
import yaml
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from rag_confidence.data.audit import sha256_file
from rag_confidence.evaluation.confidence_metrics import (
    best_f1_threshold,
    classification_metrics,
    selective_curve,
)
from rag_confidence.retrieval.run_bm25 import git_commit


def grouped_bootstrap_indices(query_ids: np.ndarray, generator: np.random.Generator) -> np.ndarray:
    unique_ids = np.unique(query_ids)
    sampled_ids = generator.choice(unique_ids, size=len(unique_ids), replace=True)
    positions = {query_id: np.flatnonzero(query_ids == query_id) for query_id in unique_ids}
    return np.concatenate([positions[query_id] for query_id in sampled_ids])


def paired_bootstrap_difference(
    y_true: np.ndarray,
    proposed_scores: np.ndarray,
    baseline_scores: np.ndarray,
    query_ids: np.ndarray,
    metric: Callable[[np.ndarray, np.ndarray], float],
    *,
    replicates: int,
    seed: int,
    higher_is_better: bool = True,
) -> tuple[dict[str, float | int], np.ndarray]:
    direction = 1.0 if higher_is_better else -1.0
    observed = direction * (metric(y_true, proposed_scores) - metric(y_true, baseline_scores))
    generator = np.random.default_rng(seed)
    differences = []
    for _ in range(replicates):
        indices = grouped_bootstrap_indices(query_ids, generator)
        sampled_y = y_true[indices]
        if len(np.unique(sampled_y)) < 2:
            continue
        differences.append(
            direction
            * (
                metric(sampled_y, proposed_scores[indices])
                - metric(sampled_y, baseline_scores[indices])
            )
        )
    values = np.asarray(differences, dtype=np.float64)
    if not len(values):
        raise RuntimeError("No valid bootstrap replicates")
    summary = {
        "observed_improvement": float(observed),
        "ci_lower": float(np.quantile(values, 0.025)),
        "ci_upper": float(np.quantile(values, 0.975)),
        "valid_replicates": int(len(values)),
        "probability_improvement_gt_zero": float((values > 0).mean()),
    }
    return summary, values


def aurc(y_true: np.ndarray, scores: np.ndarray) -> float:
    return float(selective_curve(y_true, scores)["aurc_discrete"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confidence-run", type=Path, required=True)
    parser.add_argument("--features-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("results/runs"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    experiment = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    selected = experiment["internal_selection"]
    cutoff = int(selected["primary_k"])
    seed = int(experiment["seed"])
    replicates = int(experiment["bootstrap"]["replicates"])
    feature_columns = list(experiment["feature_set"]["columns"])
    confidence_run = args.confidence_run.resolve()
    confidence_manifest = json.loads((confidence_run / "manifest.json").read_text(encoding="utf-8"))
    if confidence_manifest["final_test_used"]:
        raise PermissionError("Robustness analysis refuses final-test predictions")
    if confidence_manifest["run_id"] != selected["source_run_id"]:
        raise ValueError("Confidence run differs from the internally selected run")

    predictions_path = confidence_run / "selection_predictions.parquet"
    predictions = pd.read_parquet(predictions_path)
    proposed = predictions[
        (predictions["context_k"] == cutoff) & (predictions["method"] == selected["calibrator"])
    ].copy()
    features_path = args.features_dir.resolve() / "features.parquet"
    labels_path = args.features_dir.resolve() / "labels.parquet"
    schema_path = args.features_dir.resolve() / "schema.json"
    features = pd.read_parquet(features_path)
    labels = pd.read_parquet(labels_path)
    selection_mask = (features["context_k"] == cutoff) & (features["research_split"] == "selection")
    selection_features = features.loc[selection_mask].reset_index(drop=True)
    selection_labels = labels.loc[selection_mask].reset_index(drop=True)
    if not selection_labels["scenario_id"].equals(proposed["scenario_id"].reset_index(drop=True)):
        raise ValueError("Selected predictions and features are not aligned")
    y_selection = selection_labels["evidence_sufficient"].astype(int).to_numpy()
    proposed_scores = proposed["probability"].to_numpy(dtype=np.float64)
    query_ids = selection_labels["query_id"].astype(str).to_numpy()
    baseline_columns = {
        "bm25": "bm25_top1_score_raw",
        "semantic": "semantic_top1_score_raw",
        "hybrid": "rrf_top1_score_raw",
    }
    metric_functions = {
        "roc_auc": (lambda y, score: float(roc_auc_score(y, score)), True),
        "pr_auc": (lambda y, score: float(average_precision_score(y, score)), True),
        "aurc": (aurc, False),
    }
    bootstrap_summary = {}
    bootstrap_rows = []
    for baseline_name, column in baseline_columns.items():
        baseline_scores = selection_features[column].to_numpy(dtype=np.float64)
        bootstrap_summary[baseline_name] = {}
        for metric_name, (function, higher_is_better) in metric_functions.items():
            summary, values = paired_bootstrap_difference(
                y_selection,
                proposed_scores,
                baseline_scores,
                query_ids,
                function,
                replicates=replicates,
                seed=seed,
                higher_is_better=higher_is_better,
            )
            bootstrap_summary[baseline_name][metric_name] = summary
            bootstrap_rows.extend(
                {
                    "baseline": baseline_name,
                    "metric": metric_name,
                    "replicate": replicate,
                    "improvement": float(value),
                }
                for replicate, value in enumerate(values)
            )

    fit_mask = (features["context_k"] == cutoff) & (features["research_split"] == "fit")
    fit_features = features.loc[fit_mask].reset_index(drop=True)
    fit_labels = labels.loc[fit_mask].reset_index(drop=True)
    y_fit = fit_labels["evidence_sufficient"].astype(int).to_numpy()
    feature_groups = {
        "lexical_only": [column for column in feature_columns if column.startswith("bm25_")],
        "semantic_only": [column for column in feature_columns if column.startswith("semantic_")],
        "hybrid_only": [column for column in feature_columns if column.startswith("rrf_")],
        "retrieval_scores": [
            column
            for column in feature_columns
            if column.startswith(("bm25_", "semantic_", "rrf_"))
        ],
        "full_core_v1": feature_columns,
    }
    model_config = experiment["logistic_regression"]
    ablation_rows = []
    for group_name, columns in feature_groups.items():
        pipeline = Pipeline(
            [
                ("standardize", StandardScaler()),
                (
                    "logistic",
                    LogisticRegression(
                        C=float(model_config["C"]),
                        class_weight=model_config["class_weight"],
                        max_iter=int(model_config["max_iter"]),
                        solver=str(model_config["solver"]),
                        random_state=seed,
                    ),
                ),
            ]
        )
        pipeline.fit(fit_features[columns].astype(float), y_fit)
        probability = pipeline.predict_proba(selection_features[columns].astype(float))[:, 1]
        balanced = best_f1_threshold(y_selection, probability)
        fixed = classification_metrics(y_selection, probability, 0.5)
        ablation_rows.append(
            {
                "group": group_name,
                "feature_count": len(columns),
                "roc_auc": fixed["roc_auc"],
                "pr_auc": fixed["pr_auc"],
                "aurc": aurc(y_selection, probability),
                "balanced_f1": balanced["f1"],
            }
        )

    started = datetime.now(timezone.utc)
    config = {
        "method": "paired_grouped_bootstrap_and_ablation",
        "source_run_id": confidence_manifest["run_id"],
        "context_k": cutoff,
        "calibrator": selected["calibrator"],
        "replicates": replicates,
        "seed": seed,
        "grouped_by": "query_id",
        "paired": True,
        "feature_groups": feature_groups,
    }
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    run_id = f"{started.strftime('%Y%m%d-%H%M%S')}_robustness-k{cutoff}_{config_hash[:8]}"
    run_dir = args.output_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    summary_path = run_dir / "metrics.json"
    bootstrap_path = run_dir / "bootstrap_replicates.parquet"
    ablation_path = run_dir / "ablation.parquet"
    config_path = run_dir / "config.json"
    summary = {
        "bootstrap": bootstrap_summary,
        "ablation": ablation_rows,
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    pd.DataFrame(bootstrap_rows).to_parquet(bootstrap_path, index=False, compression="zstd")
    pd.DataFrame(ablation_rows).to_parquet(ablation_path, index=False, compression="zstd")
    config_path.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths = {
        "metrics": summary_path,
        "bootstrap": bootstrap_path,
        "ablation": ablation_path,
        "config": config_path,
    }
    manifest = {
        "run_id": run_id,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(Path.cwd().resolve()),
        "python": platform.python_version(),
        "scikit_learn": sklearn.__version__,
        "config_sha256": config_hash,
        "source_confidence_manifest_sha256": sha256_file(confidence_run / "manifest.json"),
        "sources": {
            "predictions": sha256_file(predictions_path),
            "features": sha256_file(features_path),
            "labels": sha256_file(labels_path),
            "schema": sha256_file(schema_path),
        },
        "final_test_used": False,
        "artifacts": {name: sha256_file(path) for name, path in paths.items()},
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"RUN_ID={run_id}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
