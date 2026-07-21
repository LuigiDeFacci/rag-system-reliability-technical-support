"""Train fixed logistic models, calibrate separately and evaluate internal selection."""

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
import sklearn
import yaml
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from rag_confidence.data.audit import sha256_file
from rag_confidence.evaluation.confidence_metrics import (
    best_f1_threshold,
    classification_metrics,
    expected_calibration_error,
    selective_summary,
    threshold_for_maximum_coverage_at_risk,
)
from rag_confidence.retrieval.run_bm25 import git_commit


def scenario_breakdown(
    labels: pd.DataFrame, probabilities: np.ndarray, threshold: float = 0.5
) -> dict[str, Any]:
    frame = labels.copy()
    frame["probability"] = probabilities
    frame["prediction"] = frame["probability"] >= threshold
    rows = {}
    for scenario_type, group in frame.groupby("scenario_type", sort=True):
        y = group["evidence_sufficient"].astype(int)
        rows[str(scenario_type)] = {
            "rows": int(len(group)),
            "positive_rate": float(y.mean()),
            "mean_probability": float(group["probability"].mean()),
            "predicted_positive_rate_at_0_5": float(group["prediction"].mean()),
            "accuracy_at_0_5": float((group["prediction"].astype(int) == y).mean()),
        }
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/experiment.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("results/runs"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features_dir = args.features_dir.resolve()
    feature_manifest_path = features_dir / "manifest.json"
    feature_manifest = json.loads(feature_manifest_path.read_text(encoding="utf-8"))
    if feature_manifest["final_test_used"]:
        raise PermissionError("Internal training refuses final-test feature artifacts")
    features_path = features_dir / "features.parquet"
    labels_path = features_dir / "labels.parquet"
    schema_path = features_dir / "schema.json"
    features = pd.read_parquet(features_path)
    labels = pd.read_parquet(labels_path)
    if not features["scenario_id"].equals(labels["scenario_id"]):
        raise ValueError("Feature and label rows are not aligned")

    experiment = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    feature_columns = list(experiment["feature_set"]["columns"])
    missing = set(feature_columns) - set(features.columns)
    if missing:
        raise KeyError(f"Configured features are missing: {sorted(missing)}")
    model_config = experiment["logistic_regression"]
    calibration_config = experiment["calibration"]
    seed = int(experiment["seed"])
    training_split = str(experiment["training_split"])
    calibration_split = str(calibration_config["fit_split"])
    selection_split = str(experiment["threshold_selection_split"])
    cutoffs = sorted(int(value) for value in features["context_k"].unique())

    started = datetime.now(timezone.utc)
    config = {
        "method": "logistic_core_v1_per_k",
        "feature_set": experiment["feature_set"],
        "logistic_regression": model_config,
        "calibration": calibration_config,
        "training_split": training_split,
        "calibration_split": calibration_split,
        "selection_split": selection_split,
        "cutoffs": cutoffs,
        "seed": seed,
        "policy_criteria": {
            "conservative": "maximum coverage with empirical risk <= 0.10",
            "balanced": "maximum F1",
            "expansive": "maximum coverage with empirical risk <= 0.20",
        },
    }
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    run_id = f"{started.strftime('%Y%m%d-%H%M%S')}_confidence-logreg_{config_hash[:8]}"
    run_dir = args.output_root.resolve() / run_id
    models_dir = run_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=False)

    metrics: dict[str, Any] = {}
    prediction_rows = []
    reliability_rows = []
    coefficient_rows = []
    baseline_signals = {
        "bm25_threshold": "bm25_top1_score_raw",
        "semantic_threshold": "semantic_top1_score_raw",
        "hybrid_threshold": "rrf_top1_score_raw",
    }
    for cutoff in cutoffs:
        mask_k = features["context_k"] == cutoff
        split_frames = {}
        for split in (training_split, calibration_split, selection_split):
            mask = mask_k & (features["research_split"] == split)
            split_frames[split] = (
                features.loc[mask],
                labels.loc[mask].reset_index(drop=True),
            )
        fit_features, fit_labels = split_frames[training_split]
        calibration_features, calibration_labels = split_frames[calibration_split]
        selection_features, selection_labels = split_frames[selection_split]
        x_fit = fit_features[feature_columns].astype(float)
        x_calibration = calibration_features[feature_columns].astype(float)
        x_selection = selection_features[feature_columns].astype(float)
        y_fit = fit_labels["evidence_sufficient"].astype(int).to_numpy()
        y_calibration = calibration_labels["evidence_sufficient"].astype(int).to_numpy()
        y_selection = selection_labels["evidence_sufficient"].astype(int).to_numpy()

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
        pipeline.fit(x_fit, y_fit)
        raw_calibration = pipeline.predict_proba(x_calibration)[:, 1]
        raw_selection = pipeline.predict_proba(x_selection)[:, 1]
        calibration_decision = pipeline.decision_function(x_calibration).reshape(-1, 1)
        selection_decision = pipeline.decision_function(x_selection).reshape(-1, 1)
        platt = LogisticRegression(C=1_000_000.0, max_iter=2000, solver="lbfgs")
        platt.fit(calibration_decision, y_calibration)
        isotonic = IsotonicRegression(out_of_bounds="clip")
        isotonic.fit(raw_calibration, y_calibration)
        probabilities = {
            "raw": raw_selection,
            "platt": platt.predict_proba(selection_decision)[:, 1],
            "isotonic": isotonic.predict(raw_selection),
        }

        method_metrics = {}
        for method, probability in probabilities.items():
            ece, bins = expected_calibration_error(
                y_selection, probability, int(calibration_config["ece_bins"])
            )
            policies = {
                "conservative": threshold_for_maximum_coverage_at_risk(
                    y_selection, probability, 0.10
                ),
                "balanced": best_f1_threshold(y_selection, probability),
                "expansive": threshold_for_maximum_coverage_at_risk(y_selection, probability, 0.20),
            }
            method_metrics[method] = {
                "classification_at_0_5": classification_metrics(y_selection, probability, 0.5),
                "brier": float(brier_score_loss(y_selection, probability)),
                "ece": ece,
                "ece_bins": int(calibration_config["ece_bins"]),
                "ece_binning": str(calibration_config["ece_binning"]),
                "selective": selective_summary(y_selection, probability),
                "policies": policies,
                "scenario_breakdown": scenario_breakdown(selection_labels, probability, 0.5),
            }
            for row, value in zip(
                selection_labels.itertuples(index=False), probability, strict=True
            ):
                prediction_rows.append(
                    {
                        "scenario_id": str(row.scenario_id),
                        "query_id": str(row.query_id),
                        "research_split": selection_split,
                        "context_k": cutoff,
                        "scenario_type": str(row.scenario_type),
                        "evidence_sufficient": bool(row.evidence_sufficient),
                        "method": method,
                        "probability": float(value),
                    }
                )
            for bin_row in bins:
                reliability_rows.append({"context_k": cutoff, "method": method, **bin_row})

        baselines = {}
        for baseline, column in baseline_signals.items():
            scores = selection_features[column].to_numpy(dtype=np.float64)
            baselines[baseline] = {
                "signal": column,
                "selection_best_f1": best_f1_threshold(y_selection, scores),
            }
        selected_calibrator = min(
            probabilities,
            key=lambda method: (
                method_metrics[method]["brier"],
                ("raw", "platt", "isotonic").index(method),
            ),
        )
        metrics[f"k{cutoff}"] = {
            "rows": {
                training_split: int(len(y_fit)),
                calibration_split: int(len(y_calibration)),
                selection_split: int(len(y_selection)),
            },
            "prevalence": {
                training_split: float(y_fit.mean()),
                calibration_split: float(y_calibration.mean()),
                selection_split: float(y_selection.mean()),
            },
            "calibration_methods": method_metrics,
            "selected_calibrator_by_selection_brier": selected_calibrator,
            "threshold_baselines": baselines,
        }
        coefficients = pipeline.named_steps["logistic"].coef_[0]
        for feature, coefficient in zip(feature_columns, coefficients, strict=True):
            coefficient_rows.append(
                {
                    "context_k": cutoff,
                    "feature": feature,
                    "standardized_coefficient": float(coefficient),
                }
            )
        joblib.dump(
            {
                "context_k": cutoff,
                "feature_columns": feature_columns,
                "pipeline": pipeline,
                "platt": platt,
                "isotonic": isotonic,
                "selected_calibrator": selected_calibrator,
            },
            models_dir / f"confidence_k{cutoff}.joblib",
        )

    predictions = pd.DataFrame(prediction_rows)
    reliability = pd.DataFrame(reliability_rows)
    coefficients = pd.DataFrame(coefficient_rows)
    paths = {
        "predictions": run_dir / "selection_predictions.parquet",
        "reliability": run_dir / "reliability_bins.parquet",
        "coefficients": run_dir / "coefficients.parquet",
        "metrics": run_dir / "metrics.json",
        "config": run_dir / "config.json",
    }
    predictions.to_parquet(paths["predictions"], index=False, compression="zstd")
    reliability.to_parquet(paths["reliability"], index=False, compression="zstd")
    coefficients.to_parquet(paths["coefficients"], index=False, compression="zstd")
    paths["metrics"].write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["config"].write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    model_hashes = {path.name: sha256_file(path) for path in sorted(models_dir.glob("*.joblib"))}
    manifest = {
        "run_id": run_id,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(Path.cwd().resolve()),
        "python": platform.python_version(),
        "scikit_learn": sklearn.__version__,
        "config_sha256": config_hash,
        "feature_manifest": feature_manifest,
        "source_artifacts": {
            "features": sha256_file(features_path),
            "labels": sha256_file(labels_path),
            "schema": sha256_file(schema_path),
        },
        "final_test_used": False,
        "artifacts": {
            **{name: sha256_file(path) for name, path in paths.items()},
            "models": model_hashes,
        },
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"RUN_ID={run_id}")
    print(f"RUN_DIR={run_dir}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
