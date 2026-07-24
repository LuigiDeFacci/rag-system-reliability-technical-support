"""Apply the frozen confidence protocol to the local final holdout.

This command verifies source manifests, applies the selected model and
thresholds, and writes a new immutable run. It must not be used for selection.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np
import pandas as pd
import sklearn
import yaml
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from rag_confidence.data.audit import sha256_file
from rag_confidence.evaluation.confidence_metrics import (
    classification_metrics,
    expected_calibration_error,
    selective_curve,
    selective_summary,
)
from rag_confidence.evaluation.evaluate_hard_negatives import feature_row
from rag_confidence.evaluation.run_robustness import paired_bootstrap_difference
from rag_confidence.models.train_internal import scenario_breakdown
from rag_confidence.retrieval.run_bm25 import enforce_test_gate, git_commit


def require_frozen_gate(
    gate_path: Path, spec_path: Path, *, allow_test: bool, repository_root: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    # Opening the holdout is an explicit, auditable boundary in the workflow.
    enforce_test_gate(("final_test",), allow_test, gate_path)
    gate = yaml.safe_load(gate_path.read_text(encoding="utf-8"))
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    expected_hash = str(gate["requirements"]["config_hash"])
    if sha256_file(spec_path) != expected_hash:
        raise PermissionError("Final-test specification hash differs from the frozen gate")
    frozen_commit = str(gate["requirements"]["git_commit"])
    current_commit = git_commit(repository_root)
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", frozen_commit, str(current_commit)],
        cwd=repository_root,
        check=False,
        capture_output=True,
    )
    if ancestry.returncode != 0:
        raise PermissionError("Current commit does not descend from the frozen protocol commit")
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        raise PermissionError("Final-test evaluation requires a clean Git worktree")
    return gate, spec


def evaluate_subset(
    frame: pd.DataFrame,
    policy_thresholds: dict[str, float],
    baseline_specs: dict[str, dict[str, Any]],
    *,
    ece_bins: int,
) -> dict[str, Any]:
    y = frame["evidence_sufficient"].astype(int).to_numpy()
    probability = frame["probability"].to_numpy(dtype=np.float64)
    ece, _ = expected_calibration_error(y, probability, ece_bins)
    return {
        "rows": int(len(frame)),
        "positive": int(y.sum()),
        "prevalence": float(y.mean()),
        "classification_at_0_5": classification_metrics(y, probability, 0.5),
        "brier": float(brier_score_loss(y, probability)),
        "ece": ece,
        "ece_bins": ece_bins,
        "ece_binning": "equal_width",
        "selective": selective_summary(y, probability),
        "policies": {
            name: classification_metrics(y, probability, threshold)
            for name, threshold in policy_thresholds.items()
        },
        "baselines": {
            name: {
                "signal": values["signal"],
                "frozen_threshold": classification_metrics(
                    y,
                    frame[str(values["signal"])].to_numpy(dtype=np.float64),
                    float(values["threshold"]),
                ),
                "selective": selective_summary(
                    y, frame[str(values["signal"])].to_numpy(dtype=np.float64)
                ),
            }
            for name, values in baseline_specs.items()
        },
    }


def bootstrap_comparisons(
    frame: pd.DataFrame, *, replicates: int, seed: int
) -> tuple[dict[str, Any], pd.DataFrame]:
    y = frame["evidence_sufficient"].astype(int).to_numpy()
    proposed = frame["probability"].to_numpy(dtype=np.float64)
    query_ids = frame["query_id"].astype(str).to_numpy()
    baselines = {
        "bm25": frame["bm25_top1_score_raw"].to_numpy(dtype=np.float64),
        "semantic": frame["semantic_top1_score_raw"].to_numpy(dtype=np.float64),
        "hybrid": frame["rrf_top1_score_raw"].to_numpy(dtype=np.float64),
    }
    metric_functions: dict[str, tuple[Callable[[np.ndarray, np.ndarray], float], bool]] = {
        "roc_auc": (lambda labels, score: float(roc_auc_score(labels, score)), True),
        "pr_auc": (lambda labels, score: float(average_precision_score(labels, score)), True),
        "aurc": (
            lambda labels, score: float(selective_curve(labels, score)["aurc_discrete"]),
            False,
        ),
    }
    summary = {}
    rows = []
    for baseline_name, baseline_scores in baselines.items():
        summary[baseline_name] = {}
        for metric_name, (function, higher_is_better) in metric_functions.items():
            result, values = paired_bootstrap_difference(
                y,
                proposed,
                baseline_scores,
                query_ids,
                function,
                replicates=replicates,
                seed=seed,
                higher_is_better=higher_is_better,
            )
            summary[baseline_name][metric_name] = result
            rows.extend(
                {
                    "baseline": baseline_name,
                    "metric": metric_name,
                    "replicate": index,
                    "improvement": float(value),
                }
                for index, value in enumerate(values)
            )
    return summary, pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bm25-run", type=Path, required=True)
    parser.add_argument("--semantic-run", type=Path, required=True)
    parser.add_argument("--hybrid-run", type=Path, required=True)
    parser.add_argument("--confidence-run", type=Path, required=True)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/techqa_v1"))
    parser.add_argument("--spec", type=Path, default=Path("configs/final_test_spec.yaml"))
    parser.add_argument("--gate", type=Path, default=Path("configs/final_test.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("results/runs"))
    parser.add_argument("--allow-test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repository_root = Path.cwd().resolve()
    _, spec = require_frozen_gate(
        args.gate.resolve(),
        args.spec.resolve(),
        allow_test=args.allow_test,
        repository_root=repository_root,
    )
    cutoff = int(spec["retrieval"]["primary_k"])
    run_paths = {
        "bm25": args.bm25_run.resolve(),
        "semantic": args.semantic_run.resolve(),
        "hybrid": args.hybrid_run.resolve(),
    }
    run_manifests = {
        name: json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        for name, path in run_paths.items()
    }
    if not all(manifest["final_test_used"] for manifest in run_manifests.values()):
        raise PermissionError("Every retrieval source must be a gated final-test run")
    rankings = {
        name: pd.read_parquet(path / "rankings.parquet").set_index("query_id")
        for name, path in run_paths.items()
    }
    query_id_sets = [set(frame.index) for frame in rankings.values()]
    if not all(values == query_id_sets[0] for values in query_id_sets[1:]):
        raise ValueError("Final retrieval runs contain different query IDs")

    processed_dir = args.processed_dir.resolve()
    questions_path = processed_dir / "questions.parquet"
    documents_path = processed_dir / "documents.parquet"
    if sha256_file(questions_path) != str(spec["dataset"]["questions_sha256"]):
        raise ValueError("Questions hash differs from the frozen specification")
    if sha256_file(documents_path) != str(spec["dataset"]["documents_sha256"]):
        raise ValueError("Documents hash differs from the frozen specification")
    questions = pd.read_parquet(questions_path)
    questions = questions[questions["research_split"] == "final_test"].copy()
    if len(questions) != int(spec["dataset"]["expected_rows"]):
        raise ValueError("Final-test row count differs from the frozen specification")
    questions = questions.set_index("query_id")
    if set(questions.index) != query_id_sets[0]:
        raise ValueError("Questions and rankings contain different final-test IDs")

    hybrid_evaluation = pd.read_parquet(run_paths["hybrid"] / "evaluation.parquet").set_index(
        "query_id"
    )
    feature_rows = []
    label_rows = []
    for query_id, question in questions.iterrows():
        feature_rows.append(
            feature_row(
                str(query_id),
                str(question["query_text"]),
                rankings["bm25"].loc[query_id],
                rankings["semantic"].loc[query_id],
                rankings["hybrid"].loc[query_id],
                cutoff,
            )
        )
        sufficient = bool(hybrid_evaluation.loc[query_id, f"evidence_at_{cutoff}"])
        if not bool(question["answerable"]):
            scenario_type = "native_unanswerable"
        elif sufficient:
            scenario_type = "natural_sufficient"
        else:
            scenario_type = "natural_retrieval_miss"
        label_rows.append(
            {
                "query_id": str(query_id),
                "evidence_sufficient": sufficient,
                "scenario_type": scenario_type,
                "exact_duplicate_with_official_train": bool(
                    question["exact_duplicate_with_official_train"]
                ),
                "near_duplicate_with_official_train": bool(
                    question["near_duplicate_with_official_train"]
                ),
            }
        )
    features = pd.DataFrame(feature_rows)
    labels = pd.DataFrame(label_rows)
    if not features["query_id"].equals(labels["query_id"]):
        raise ValueError("Final features and labels are not aligned")

    confidence_run = args.confidence_run.resolve()
    confidence_manifest_path = confidence_run / "manifest.json"
    model_spec = spec["model"]
    if sha256_file(confidence_manifest_path) != str(model_spec["source_manifest_sha256"]):
        raise ValueError("Confidence manifest differs from the frozen specification")
    confidence_manifest = json.loads(confidence_manifest_path.read_text(encoding="utf-8"))
    if confidence_manifest["run_id"] != str(model_spec["source_run_id"]):
        raise ValueError("Confidence run ID differs from the frozen specification")
    model_path = confidence_run / str(model_spec["artifact"])
    if sha256_file(model_path) != str(model_spec["artifact_sha256"]):
        raise ValueError("Frozen confidence model hash mismatch")
    model_bundle = joblib.load(model_path)
    if model_bundle["selected_calibrator"] != str(model_spec["calibrator"]):
        raise ValueError("Frozen calibrator mismatch")
    feature_columns = list(model_bundle["feature_columns"])
    probability = model_bundle["pipeline"].predict_proba(features[feature_columns].astype(float))[
        :, 1
    ]
    predictions = labels.copy()
    predictions["probability"] = probability
    for column in ("bm25_top1_score_raw", "semantic_top1_score_raw", "rrf_top1_score_raw"):
        predictions[column] = features[column].to_numpy(dtype=np.float64)

    policy_thresholds = {name: float(value) for name, value in spec["policies"].items()}
    baseline_specs = dict(spec["baselines"])
    evaluation_spec = spec["evaluation"]
    subsets = {
        "official_dev": predictions,
        "dev_clean_exact": predictions[~predictions["exact_duplicate_with_official_train"]],
        "dev_clean_near": predictions[~predictions["near_duplicate_with_official_train"]],
    }
    subset_metrics = {
        name: evaluate_subset(
            frame,
            policy_thresholds,
            baseline_specs,
            ece_bins=int(evaluation_spec["ece_bins"]),
        )
        for name, frame in subsets.items()
    }
    subset_metrics["official_dev"]["scenario_breakdown_at_0_5"] = scenario_breakdown(
        predictions[["scenario_type", "evidence_sufficient"]], probability, 0.5
    )
    bootstrap_summary, bootstrap_rows = bootstrap_comparisons(
        predictions,
        replicates=int(evaluation_spec["bootstrap_replicates"]),
        seed=int(evaluation_spec["bootstrap_seed"]),
    )
    _, reliability = expected_calibration_error(
        predictions["evidence_sufficient"].astype(int).to_numpy(),
        probability,
        int(evaluation_spec["ece_bins"]),
    )
    retrieval_metrics = {
        name: json.loads((path / "metrics.json").read_text(encoding="utf-8"))
        for name, path in run_paths.items()
    }
    metrics = {
        "scope": "frozen_final_test",
        "subsets": subset_metrics,
        "paired_grouped_bootstrap": bootstrap_summary,
        "retrieval": retrieval_metrics,
        "no_refit_or_recalibration": True,
    }

    started = datetime.now(timezone.utc)
    config_hash = sha256_file(args.spec.resolve())
    run_id = f"{started.strftime('%Y%m%d-%H%M%S')}_final-test-k{cutoff}_{config_hash[:8]}"
    run_dir = args.output_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    paths = {
        "predictions": run_dir / "predictions.parquet",
        "features": run_dir / "features.parquet",
        "reliability": run_dir / "reliability_bins.parquet",
        "bootstrap": run_dir / "bootstrap_replicates.parquet",
        "metrics": run_dir / "metrics.json",
        "spec": run_dir / "frozen_spec.yaml",
    }
    predictions.to_parquet(paths["predictions"], index=False, compression="zstd")
    features.to_parquet(paths["features"], index=False, compression="zstd")
    pd.DataFrame(reliability).to_parquet(paths["reliability"], index=False, compression="zstd")
    bootstrap_rows.to_parquet(paths["bootstrap"], index=False, compression="zstd")
    paths["metrics"].write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["spec"].write_text(
        yaml.safe_dump(spec, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    manifest = {
        "run_id": run_id,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(repository_root),
        "python": platform.python_version(),
        "scikit_learn": sklearn.__version__,
        "frozen_spec_sha256": config_hash,
        "source_runs": {name: manifest["run_id"] for name, manifest in run_manifests.items()},
        "sources": {
            "questions": sha256_file(questions_path),
            "documents": sha256_file(documents_path),
            "confidence_manifest": sha256_file(confidence_manifest_path),
            "model": sha256_file(model_path),
            **{
                f"{name}_manifest": sha256_file(path / "manifest.json")
                for name, path in run_paths.items()
            },
        },
        "final_test_used": True,
        "no_refit_or_recalibration": True,
        "artifacts": {name: sha256_file(path) for name, path in paths.items()},
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"RUN_ID={run_id}")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
