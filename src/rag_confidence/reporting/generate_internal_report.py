"""Generate reproducible internal-selection tables and figures.

This command intentionally refuses artifacts that used the final test. The generated
outputs are descriptive material for protocol development, not final-test results.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from rag_confidence.data.audit import sha256_file
from rag_confidence.evaluation.confidence_metrics import selective_curve
from rag_confidence.retrieval.run_bm25 import git_commit


METHOD_LABELS = {
    "raw": "Regressão logística",
    "platt": "Platt",
    "isotonic": "Isotônica",
    "bm25": "BM25 top-1",
    "semantic": "Semântico top-1",
    "hybrid": "RRF top-1",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confidence-run", type=Path, required=True)
    parser.add_argument("--robustness-run", type=Path, required=True)
    parser.add_argument("--features-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--context-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, required=True)
    return parser.parse_args()


def load_internal_manifest(directory: Path) -> dict[str, Any]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("final_test_used") is not False:
        raise PermissionError(f"Internal reporting refuses final-test artifact: {directory}")
    return manifest


def save_figure(figure: plt.Figure, output_dir: Path, stem: str) -> list[Path]:
    paths = [output_dir / f"{stem}.png", output_dir / f"{stem}.svg"]
    figure.savefig(paths[0], dpi=180, bbox_inches="tight")
    figure.savefig(paths[1], bbox_inches="tight")
    plt.close(figure)
    return paths


def calibration_figure(reliability: pd.DataFrame, cutoff: int) -> plt.Figure:
    figure, axis = plt.subplots(figsize=(6.4, 5.2))
    axis.plot([0, 1], [0, 1], linestyle="--", color="0.5", label="Calibração perfeita")
    for method in ("raw", "platt", "isotonic"):
        rows = reliability[
            (reliability["context_k"] == cutoff)
            & (reliability["method"] == method)
            & (reliability["count"] > 0)
        ]
        axis.plot(
            rows["mean_confidence"],
            rows["fraction_positive"],
            marker="o",
            linewidth=1.8,
            label=METHOD_LABELS[method],
        )
    axis.set(xlabel="Probabilidade média", ylabel="Fração positiva", xlim=(0, 1), ylim=(0, 1))
    axis.set_title(f"Diagrama de confiabilidade — seleção interna, k={cutoff}")
    axis.grid(alpha=0.25)
    axis.legend(frameon=False)
    figure.tight_layout()
    return figure


def risk_coverage_figure(
    predictions: pd.DataFrame,
    features: pd.DataFrame,
    labels: pd.DataFrame,
    cutoff: int,
) -> plt.Figure:
    mask = (features["context_k"] == cutoff) & (features["research_split"] == "selection")
    selection_features = features.loc[mask].reset_index(drop=True)
    selection_labels = labels.loc[mask].reset_index(drop=True)
    proposed = predictions[
        (predictions["context_k"] == cutoff) & (predictions["method"] == "raw")
    ].reset_index(drop=True)
    if not proposed["scenario_id"].equals(selection_labels["scenario_id"]):
        raise ValueError("Predictions and selection labels are not aligned")
    y = selection_labels["evidence_sufficient"].astype(int).to_numpy()
    signals = {
        "raw": proposed["probability"].to_numpy(float),
        "bm25": selection_features["bm25_top1_score_raw"].to_numpy(float),
        "semantic": selection_features["semantic_top1_score_raw"].to_numpy(float),
        "hybrid": selection_features["rrf_top1_score_raw"].to_numpy(float),
    }
    figure, axis = plt.subplots(figsize=(6.8, 5.2))
    for method, scores in signals.items():
        curve = selective_curve(y, scores)
        axis.plot(
            curve["coverage"],
            curve["risk"],
            linewidth=2.0 if method == "raw" else 1.5,
            label=f"{METHOD_LABELS[method]} (AURC={curve['aurc_discrete']:.3f})",
        )
    axis.set(xlabel="Cobertura", ylabel="Risco seletivo", xlim=(0, 1), ylim=(0, 1))
    axis.set_title(f"Risco × cobertura — seleção interna, k={cutoff}")
    axis.grid(alpha=0.25)
    axis.legend(frameon=False)
    figure.tight_layout()
    return figure


def ablation_figure(ablation: pd.DataFrame) -> plt.Figure:
    labels = {
        "lexical_only": "Lexical",
        "semantic_only": "Semântico",
        "hybrid_only": "Híbrido",
        "retrieval_scores": "Scores",
        "full_core_v1": "Completo",
    }
    frame = ablation.copy()
    frame["group_label"] = frame["group"].map(labels)
    metrics = [("roc_auc", "ROC-AUC"), ("pr_auc", "PR-AUC"), ("balanced_f1", "F1")]
    x = np.arange(len(frame))
    width = 0.24
    figure, axis = plt.subplots(figsize=(8.2, 5.2))
    for index, (column, label) in enumerate(metrics):
        axis.bar(x + (index - 1) * width, frame[column], width, label=label)
    axis.set_xticks(x, frame["group_label"])
    axis.set(ylabel="Métrica", ylim=(0, 1))
    axis.set_title("Ablação de grupos de features — seleção interna, k=5")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(frameon=False, ncol=3)
    figure.tight_layout()
    return figure


def coefficient_figure(coefficients: pd.DataFrame, cutoff: int) -> plt.Figure:
    frame = coefficients[coefficients["context_k"] == cutoff].copy()
    frame["absolute"] = frame["standardized_coefficient"].abs()
    frame = frame.nlargest(12, "absolute").sort_values("standardized_coefficient")
    colors = np.where(frame["standardized_coefficient"] >= 0, "#2a6fbb", "#c4513b")
    figure, axis = plt.subplots(figsize=(8.6, 6.0))
    axis.barh(frame["feature"], frame["standardized_coefficient"], color=colors)
    axis.axvline(0, color="0.3", linewidth=0.8)
    axis.set(xlabel="Coeficiente padronizado")
    axis.set_title(f"Maiores coeficientes em módulo — seleção interna, k={cutoff}")
    axis.grid(axis="x", alpha=0.2)
    figure.tight_layout()
    return figure


def error_table(predictions: pd.DataFrame, cutoff: int, threshold: float) -> pd.DataFrame:
    frame = predictions[
        (predictions["context_k"] == cutoff) & (predictions["method"] == "raw")
    ].copy()
    frame["prediction"] = (frame["probability"] >= threshold).astype(int)
    frame["label"] = frame["evidence_sufficient"].astype(int)
    frame["error_type"] = np.select(
        [
            (frame["label"] == 0) & (frame["prediction"] == 1),
            (frame["label"] == 1) & (frame["prediction"] == 0),
        ],
        ["false_positive", "false_negative"],
        default="correct",
    )
    return frame[
        [
            "query_id",
            "scenario_id",
            "scenario_type",
            "label",
            "probability",
            "prediction",
            "error_type",
        ]
    ].sort_values(["error_type", "probability"], ascending=[True, False])


def main() -> None:
    args = parse_args()
    confidence_run = args.confidence_run.resolve()
    robustness_run = args.robustness_run.resolve()
    features_dir = args.features_dir.resolve()
    output_dir = args.output_dir.resolve()
    confidence_manifest = load_internal_manifest(confidence_run)
    robustness_manifest = load_internal_manifest(robustness_run)
    feature_manifest = load_internal_manifest(features_dir)
    if robustness_manifest.get("source_confidence_manifest_sha256") != sha256_file(
        confidence_run / "manifest.json"
    ):
        raise ValueError("Robustness run does not reference the supplied confidence run")
    output_dir.mkdir(parents=True, exist_ok=False)

    predictions = pd.read_parquet(confidence_run / "selection_predictions.parquet")
    reliability = pd.read_parquet(confidence_run / "reliability_bins.parquet")
    coefficients = pd.read_parquet(confidence_run / "coefficients.parquet")
    ablation = pd.read_parquet(robustness_run / "ablation.parquet")
    features = pd.read_parquet(features_dir / "features.parquet")
    labels = pd.read_parquet(features_dir / "labels.parquet")

    artifacts: list[Path] = []
    artifacts += save_figure(
        calibration_figure(reliability, args.context_k), output_dir, "reliability_k5"
    )
    artifacts += save_figure(
        risk_coverage_figure(predictions, features, labels, args.context_k),
        output_dir,
        "risk_coverage_k5",
    )
    artifacts += save_figure(ablation_figure(ablation), output_dir, "feature_ablation_k5")
    artifacts += save_figure(
        coefficient_figure(coefficients, args.context_k), output_dir, "coefficients_k5"
    )

    errors = error_table(predictions, args.context_k, args.threshold)
    errors_path = output_dir / "error_analysis_k5.csv"
    errors.to_csv(errors_path, index=False)
    artifacts.append(errors_path)
    error_summary_path = output_dir / "error_summary_k5.csv"
    (
        errors.groupby(["scenario_type", "error_type"], observed=True)
        .size()
        .rename("rows")
        .reset_index()
        .to_csv(error_summary_path, index=False)
    )
    artifacts.append(error_summary_path)
    ablation_path = output_dir / "ablation_k5.csv"
    ablation.to_csv(ablation_path, index=False)
    artifacts.append(ablation_path)

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(Path.cwd().resolve()),
        "scope": "internal_selection_only",
        "context_k": args.context_k,
        "balanced_threshold": args.threshold,
        "confidence_run_id": confidence_manifest["run_id"],
        "robustness_run_id": robustness_manifest["run_id"],
        "feature_version": feature_manifest["version"],
        "final_test_used": False,
        "artifacts": {path.name: sha256_file(path) for path in artifacts},
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"OUTPUT_DIR={output_dir}")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
