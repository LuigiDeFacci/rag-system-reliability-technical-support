"""Post-hoc fixed-coverage risk table over frozen final predictions.

This analysis only summarizes existing predictions. It never fits a model, changes a
threshold or reopens the final-test gate.
"""

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
import yaml

from rag_confidence.data.audit import sha256_file
from rag_confidence.retrieval.run_bm25 import git_commit


METHOD_SIGNALS = {
    "logistic": "probability",
    "bm25": "bm25_top1_score_raw",
    "semantic": "semantic_top1_score_raw",
    "rrf": "rrf_top1_score_raw",
}


def tie_aware_risk_at_coverage(
    y_true: np.ndarray, scores: np.ndarray, coverage: float
) -> dict[str, float | int]:
    """Compute expected risk with fractional inclusion of the boundary tie.

    Fractional inclusion makes comparisons invariant to arbitrary row order when a score,
    particularly an RRF score, is shared by many queries.
    """
    if not 0 < coverage <= 1:
        raise ValueError("coverage must be in (0, 1]")
    y = np.asarray(y_true, dtype=np.int64)
    values = np.asarray(scores, dtype=np.float64)
    if len(y) != len(values) or not len(y):
        raise ValueError("Labels and scores must have the same non-zero length")
    target_mass = coverage * len(y)
    accepted_mass = 0.0
    expected_errors = 0.0
    boundary_score = float("nan")
    boundary_tie_count = 0
    boundary_fraction = 0.0
    for score in np.unique(values)[::-1]:
        mask = values == score
        count = int(mask.sum())
        remaining = target_mass - accepted_mass
        if remaining <= 0:
            break
        fraction = min(1.0, remaining / count)
        accepted_mass += fraction * count
        expected_errors += fraction * float((1 - y[mask]).sum())
        boundary_score = float(score)
        boundary_tie_count = count
        boundary_fraction = fraction
        if fraction < 1.0 or np.isclose(accepted_mass, target_mass):
            break
    return {
        "target_coverage": float(coverage),
        "accepted_mass": float(accepted_mass),
        "risk": float(expected_errors / accepted_mass),
        "boundary_score": boundary_score,
        "boundary_tie_count": boundary_tie_count,
        "boundary_fraction": float(boundary_fraction),
    }


def paired_bootstrap(
    frame: pd.DataFrame,
    coverages: list[float],
    *,
    replicates: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    y = frame["evidence_sufficient"].astype(int).to_numpy()
    scores = {
        method: frame[column].to_numpy(dtype=np.float64)
        for method, column in METHOD_SIGNALS.items()
    }
    observed_rows = []
    for method, values in scores.items():
        for coverage in coverages:
            observed_rows.append(
                {"method": method, **tie_aware_risk_at_coverage(y, values, coverage)}
            )
    generator = np.random.default_rng(seed)
    bootstrap_rows = []
    for replicate in range(replicates):
        indices = generator.integers(0, len(frame), size=len(frame))
        sampled_y = y[indices]
        for method, values in scores.items():
            sampled_scores = values[indices]
            for coverage in coverages:
                result = tie_aware_risk_at_coverage(sampled_y, sampled_scores, coverage)
                bootstrap_rows.append(
                    {
                        "replicate": replicate,
                        "method": method,
                        "coverage": coverage,
                        "risk": result["risk"],
                    }
                )
    return pd.DataFrame(observed_rows), pd.DataFrame(bootstrap_rows)


def summarize_intervals(observed: pd.DataFrame, bootstrap: pd.DataFrame) -> dict[str, Any]:
    summary: dict[str, Any] = {"methods": {}, "logistic_risk_reduction": {}}
    for (method, coverage), group in bootstrap.groupby(["method", "coverage"], sort=True):
        observed_risk = float(
            observed.loc[
                (observed["method"] == method) & np.isclose(observed["target_coverage"], coverage),
                "risk",
            ].iloc[0]
        )
        summary["methods"].setdefault(method, {})[str(coverage)] = {
            "risk": observed_risk,
            "ci_lower": float(group["risk"].quantile(0.025)),
            "ci_upper": float(group["risk"].quantile(0.975)),
        }
    pivot = bootstrap.pivot_table(
        index=["replicate", "coverage"], columns="method", values="risk"
    ).reset_index()
    observed_pivot = observed.pivot(index="target_coverage", columns="method", values="risk")
    for baseline in ("bm25", "semantic", "rrf"):
        pivot["reduction"] = pivot[baseline] - pivot["logistic"]
        summary["logistic_risk_reduction"][baseline] = {}
        for coverage, group in pivot.groupby("coverage", sort=True):
            observed_reduction = float(
                observed_pivot.loc[coverage, baseline] - observed_pivot.loc[coverage, "logistic"]
            )
            summary["logistic_risk_reduction"][baseline][str(coverage)] = {
                "risk_reduction": observed_reduction,
                "ci_lower": float(group["reduction"].quantile(0.025)),
                "ci_upper": float(group["reduction"].quantile(0.975)),
                "probability_reduction_gt_zero": float((group["reduction"] > 0).mean()),
            }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-run", type=Path, required=True)
    parser.add_argument("--gate", type=Path, default=Path("configs/final_test.yaml"))
    parser.add_argument("--output-root", type=Path, default=Path("results/runs"))
    parser.add_argument(
        "--coverages", nargs="+", type=float, default=[0.1, 0.2, 0.4, 0.6, 0.8, 1.0]
    )
    parser.add_argument("--replicates", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    final_run = args.final_run.resolve()
    manifest_path = final_run / "manifest.json"
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if source_manifest.get("final_test_used") is not True:
        raise PermissionError("Fixed-coverage reporting requires frozen final predictions")
    if source_manifest.get("no_refit_or_recalibration") is not True:
        raise PermissionError("Source run must declare no refit or recalibration")
    gate = yaml.safe_load(args.gate.read_text(encoding="utf-8"))
    if gate.get("status") != "completed_locked" or gate.get("allow_test") is not False:
        raise PermissionError("The final-test gate must remain completed and locked")
    coverages = sorted(set(float(value) for value in args.coverages))
    if not coverages or coverages[0] <= 0 or coverages[-1] > 1:
        raise ValueError("Coverages must be in (0, 1]")
    predictions_path = final_run / "predictions.parquet"
    predictions = pd.read_parquet(predictions_path)
    if predictions["query_id"].duplicated().any():
        raise ValueError("Expected one frozen prediction per query")
    observed, bootstrap = paired_bootstrap(
        predictions, coverages, replicates=args.replicates, seed=args.seed
    )
    summary = summarize_intervals(observed, bootstrap)
    summary["scope"] = "posthoc_reporting_from_frozen_final_predictions"
    summary["rows"] = int(len(predictions))
    summary["coverages"] = coverages
    summary["tie_handling"] = "fractional_expected_risk_at_boundary_score"
    summary["bootstrap"] = {
        "replicates": args.replicates,
        "seed": args.seed,
        "unit": "query_id",
        "paired": True,
    }
    summary["no_refit_recalibration_or_threshold_selection"] = True

    started = datetime.now(timezone.utc)
    config = {
        "method": "fixed_coverage_selective_risk_posthoc_report",
        "source_run_id": source_manifest["run_id"],
        "signals": METHOD_SIGNALS,
        "coverages": coverages,
        "tie_handling": summary["tie_handling"],
        "bootstrap": summary["bootstrap"],
    }
    config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()
    run_id = f"{started.strftime('%Y%m%d-%H%M%S')}_fixed-coverage_{config_hash[:8]}"
    run_dir = args.output_root.resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    paths = {
        "table": run_dir / "fixed_coverage_risk.parquet",
        "bootstrap": run_dir / "bootstrap_replicates.parquet",
        "metrics": run_dir / "metrics.json",
        "config": run_dir / "config.json",
    }
    observed.to_parquet(paths["table"], index=False, compression="zstd")
    bootstrap.to_parquet(paths["bootstrap"], index=False, compression="zstd")
    paths["metrics"].write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
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
        "source_final_manifest_sha256": sha256_file(manifest_path),
        "source_predictions_sha256": sha256_file(predictions_path),
        "final_test_used": True,
        "posthoc_reporting_only": True,
        "no_refit_recalibration_or_threshold_selection": True,
        "gate_remained_locked": True,
        "artifacts": {name: sha256_file(path) for name, path in paths.items()},
    }
    (run_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"RUN_ID={run_id}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
