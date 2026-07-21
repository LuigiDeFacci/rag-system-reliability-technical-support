"""Evaluate internal calibration and policies under reweighted class prevalence."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from rag_confidence.data.audit import sha256_file
from rag_confidence.retrieval.run_bm25 import git_commit


def prevalence_weights(y_true: np.ndarray, target_prevalence: float) -> np.ndarray:
    if not 0 < target_prevalence < 1:
        raise ValueError("Target prevalence must be strictly between zero and one")
    y = np.asarray(y_true, dtype=np.int64)
    positive = y == 1
    negative = ~positive
    if not positive.any() or not negative.any():
        raise ValueError("Both classes are required for prevalence reweighting")
    weights = np.empty(len(y), dtype=np.float64)
    weights[positive] = target_prevalence / positive.sum()
    weights[negative] = (1 - target_prevalence) / negative.sum()
    return weights


def weighted_summary(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    target_prevalence: float,
    thresholds: dict[str, float],
    n_bins: int = 10,
) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=np.int64)
    p = np.asarray(probabilities, dtype=np.float64)
    weights = prevalence_weights(y, target_prevalence)
    indices = np.minimum((p * n_bins).astype(int), n_bins - 1)
    ece = 0.0
    for bin_index in range(n_bins):
        mask = indices == bin_index
        if not mask.any():
            continue
        bin_weight = float(weights[mask].sum())
        mean_probability = float(np.average(p[mask], weights=weights[mask]))
        fraction_positive = float(np.average(y[mask], weights=weights[mask]))
        ece += bin_weight * abs(mean_probability - fraction_positive)
    policies = {}
    for name, threshold in thresholds.items():
        accepted = p >= threshold
        coverage = float(weights[accepted].sum())
        false_accepted = float(weights[accepted & (y == 0)].sum())
        policies[name] = {
            "threshold": float(threshold),
            "coverage": coverage,
            "selective_risk": 0.0 if coverage == 0 else false_accepted / coverage,
        }
    return {
        "target_prevalence": float(target_prevalence),
        "weighted_mean_probability": float(np.average(p, weights=weights)),
        "calibration_gap": float(np.average(p, weights=weights) - target_prevalence),
        "weighted_brier": float(np.average((p - y) ** 2, weights=weights)),
        "weighted_ece": float(ece),
        "ece_bins": n_bins,
        "ece_binning": "equal_width",
        "policies": policies,
    }


def bootstrap_intervals(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    targets: list[float],
    thresholds: dict[str, float],
    *,
    replicates: int,
    seed: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    y = np.asarray(y_true, dtype=np.int64)
    p = np.asarray(probabilities, dtype=np.float64)
    positive = np.flatnonzero(y == 1)
    negative = np.flatnonzero(y == 0)
    generator = np.random.default_rng(seed)
    rows = []
    for replicate in range(replicates):
        indices = np.concatenate(
            [
                generator.choice(positive, size=len(positive), replace=True),
                generator.choice(negative, size=len(negative), replace=True),
            ]
        )
        for target in targets:
            summary = weighted_summary(y[indices], p[indices], target, thresholds)
            row = {
                "replicate": replicate,
                "target_prevalence": target,
                "weighted_brier": summary["weighted_brier"],
                "weighted_ece": summary["weighted_ece"],
            }
            for name, values in summary["policies"].items():
                row[f"{name}_coverage"] = values["coverage"]
                row[f"{name}_selective_risk"] = values["selective_risk"]
            rows.append(row)
    frame = pd.DataFrame(rows)
    intervals = {}
    metric_columns = [
        column for column in frame.columns if column not in {"replicate", "target_prevalence"}
    ]
    for target, group in frame.groupby("target_prevalence", sort=True):
        intervals[str(target)] = {
            column: {
                "ci_lower": float(group[column].quantile(0.025)),
                "ci_upper": float(group[column].quantile(0.975)),
            }
            for column in metric_columns
        }
    return intervals, frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confidence-run", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("results/runs"))
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--method", default="raw")
    parser.add_argument("--targets", nargs="+", type=float, default=[0.2, 0.4, 0.6, 0.8])
    parser.add_argument("--replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    confidence_run = args.confidence_run.resolve()
    manifest_path = confidence_run / "manifest.json"
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if source_manifest["final_test_used"]:
        raise PermissionError("Prevalence sensitivity refuses final-test predictions")
    predictions_path = confidence_run / "selection_predictions.parquet"
    predictions = pd.read_parquet(predictions_path)
    frame = predictions[
        (predictions["context_k"] == args.k) & (predictions["method"] == args.method)
    ].copy()
    if frame["query_id"].duplicated().any():
        raise ValueError("Expected one prediction per query")
    y = frame["evidence_sufficient"].astype(int).to_numpy()
    probability = frame["probability"].to_numpy(dtype=np.float64)
    source_metrics_path = confidence_run / "metrics.json"
    source_metrics = json.loads(source_metrics_path.read_text(encoding="utf-8"))
    policies = source_metrics[f"k{args.k}"]["calibration_methods"][args.method]["policies"]
    thresholds = {name: float(values["threshold"]) for name, values in policies.items()}
    targets = sorted(set(float(value) for value in args.targets))
    summaries = [weighted_summary(y, probability, target, thresholds) for target in targets]
    intervals, bootstrap = bootstrap_intervals(
        y,
        probability,
        targets,
        thresholds,
        replicates=args.replicates,
        seed=args.seed,
    )
    metrics = {
        "scope": "internal_selection_prevalence_reweighting",
        "observed_prevalence": float(y.mean()),
        "targets": summaries,
        "bootstrap_intervals": intervals,
        "interpretation_limit": (
            "conditional score distributions held fixed; no claim about operational prevalence"
        ),
    }
    started = datetime.now(timezone.utc)
    config = {
        "method": "prevalence_reweighting",
        "source_run_id": source_manifest["run_id"],
        "context_k": args.k,
        "probability_method": args.method,
        "target_prevalences": targets,
        "thresholds": thresholds,
        "ece_bins": 10,
        "ece_binning": "equal_width",
        "bootstrap": {
            "replicates": args.replicates,
            "seed": args.seed,
            "unit": "query_id",
            "stratified_by": "evidence_sufficient",
        },
    }
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    run_id = f"{started.strftime('%Y%m%d-%H%M%S')}_prevalence-k{args.k}_{config_hash[:8]}"
    run_dir = args.output_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    paths = {
        "metrics": run_dir / "metrics.json",
        "bootstrap": run_dir / "bootstrap_replicates.parquet",
        "config": run_dir / "config.json",
    }
    paths["metrics"].write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    bootstrap.to_parquet(paths["bootstrap"], index=False, compression="zstd")
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
            "confidence_manifest": sha256_file(manifest_path),
            "predictions": sha256_file(predictions_path),
            "metrics": sha256_file(source_metrics_path),
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
