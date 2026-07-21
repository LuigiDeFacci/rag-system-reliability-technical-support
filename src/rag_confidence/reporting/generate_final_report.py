"""Generate the figures and tables enumerated in the frozen final-test specification."""

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
import yaml

from rag_confidence.data.audit import sha256_file
from rag_confidence.evaluation.confidence_metrics import selective_curve
from rag_confidence.retrieval.run_bm25 import git_commit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final-run", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=Path("configs/final_test_spec.yaml"))
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def error_analysis(predictions: pd.DataFrame, threshold: float) -> pd.DataFrame:
    frame = predictions.copy()
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
            "scenario_type",
            "exact_duplicate_with_official_train",
            "near_duplicate_with_official_train",
            "label",
            "probability",
            "prediction",
            "error_type",
        ]
    ].sort_values(["error_type", "probability"], ascending=[True, False])


def save_figure(figure: plt.Figure, output_dir: Path, stem: str) -> list[Path]:
    paths = [output_dir / f"{stem}.png", output_dir / f"{stem}.svg"]
    figure.savefig(paths[0], dpi=180, bbox_inches="tight")
    figure.savefig(paths[1], bbox_inches="tight")
    plt.close(figure)
    return paths


def reliability_figure(reliability: pd.DataFrame) -> plt.Figure:
    rows = reliability[reliability["count"] > 0]
    figure, axis = plt.subplots(figsize=(6.2, 5.2))
    axis.plot([0, 1], [0, 1], "--", color="0.5", label="Calibração perfeita")
    axis.plot(
        rows["mean_confidence"],
        rows["fraction_positive"],
        marker="o",
        linewidth=2,
        label="Regressão logística",
    )
    axis.set(xlabel="Probabilidade média", ylabel="Fração positiva", xlim=(0, 1), ylim=(0, 1))
    axis.set_title("Diagrama de confiabilidade — teste final, k=5")
    axis.grid(alpha=0.25)
    axis.legend(frameon=False)
    figure.tight_layout()
    return figure


def risk_coverage_figure(predictions: pd.DataFrame) -> plt.Figure:
    y = predictions["evidence_sufficient"].astype(int).to_numpy()
    signals = {
        "Regressão logística": predictions["probability"].to_numpy(float),
        "BM25 top-1": predictions["bm25_top1_score_raw"].to_numpy(float),
        "Semântico top-1": predictions["semantic_top1_score_raw"].to_numpy(float),
        "RRF top-1": predictions["rrf_top1_score_raw"].to_numpy(float),
    }
    figure, axis = plt.subplots(figsize=(6.8, 5.2))
    for name, scores in signals.items():
        curve = selective_curve(y, scores)
        axis.plot(
            curve["coverage"],
            curve["risk"],
            linewidth=2 if name == "Regressão logística" else 1.5,
            label=f"{name} (AURC={curve['aurc_discrete']:.3f})",
        )
    axis.set(xlabel="Cobertura", ylabel="Risco seletivo", xlim=(0, 1), ylim=(0, 1))
    axis.set_title("Risco × cobertura — teste final, k=5")
    axis.grid(alpha=0.25)
    axis.legend(frameon=False)
    figure.tight_layout()
    return figure


def confusion_figure(matrix: list[list[int]]) -> plt.Figure:
    values = np.asarray(matrix, dtype=int)
    figure, axis = plt.subplots(figsize=(5.2, 4.5))
    image = axis.imshow(values, cmap="Blues")
    for row in range(2):
        for column in range(2):
            axis.text(column, row, str(values[row, column]), ha="center", va="center")
    axis.set_xticks([0, 1], ["Abster", "Responder"])
    axis.set_yticks([0, 1], ["Insuficiente", "Suficiente"])
    axis.set(xlabel="Decisão", ylabel="Rótulo")
    axis.set_title("Matriz de confusão — política equilibrada")
    figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
    figure.tight_layout()
    return figure


def scenario_figure(predictions: pd.DataFrame) -> plt.Figure:
    order = ["native_unanswerable", "natural_retrieval_miss", "natural_sufficient"]
    labels = ["Não respondível", "Miss de retrieval", "Suficiente"]
    values = [
        predictions.loc[predictions["scenario_type"] == scenario, "probability"].to_numpy()
        for scenario in order
    ]
    figure, axis = plt.subplots(figsize=(7.2, 5.0))
    axis.boxplot(values, tick_labels=labels, showmeans=True)
    axis.set(ylabel="Probabilidade de evidência suficiente", ylim=(0, 1))
    axis.set_title("Confiança por tipo de cenário — teste final")
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    return figure


def summary_tables(metrics: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    subset_rows = []
    for name, values in metrics["subsets"].items():
        classification = values["classification_at_0_5"]
        balanced = values["policies"]["balanced"]
        subset_rows.append(
            {
                "subset": name,
                "rows": values["rows"],
                "positive": values["positive"],
                "prevalence": values["prevalence"],
                "roc_auc": classification["roc_auc"],
                "pr_auc": classification["pr_auc"],
                "brier": values["brier"],
                "ece": values["ece"],
                "aurc": values["selective"]["aurc_discrete"],
                "balanced_coverage": balanced["coverage"],
                "balanced_risk": balanced["selective_risk"],
                "balanced_f1": balanced["f1"],
            }
        )
    retrieval_rows = []
    for method, run_metrics in metrics["retrieval"].items():
        values = run_metrics["final_test"]
        row = {"method": method, "mrr": values["containing_chunk"]["mrr"]}
        for cutoff in (1, 3, 5, 10):
            row[f"context_recall_at_{cutoff}"] = values[f"answerable_context_recall_at_{cutoff}"]
            row[f"ndcg_at_{cutoff}"] = values["containing_chunk"][f"ndcg_at_{cutoff}"]
        retrieval_rows.append(row)
    bootstrap_rows = []
    for baseline, baseline_metrics in metrics["paired_grouped_bootstrap"].items():
        for metric, values in baseline_metrics.items():
            bootstrap_rows.append({"baseline": baseline, "metric": metric, **values})
    return pd.DataFrame(subset_rows), pd.DataFrame(retrieval_rows), pd.DataFrame(bootstrap_rows)


def main() -> None:
    args = parse_args()
    final_run = args.final_run.resolve()
    source_manifest_path = final_run / "manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    if source_manifest.get("final_test_used") is not True:
        raise PermissionError("Final reporting requires a final-test run")
    if source_manifest.get("no_refit_or_recalibration") is not True:
        raise PermissionError("Final reporting requires a no-refit run")
    spec_path = args.spec.resolve()
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    if sha256_file(spec_path) != source_manifest["frozen_spec_sha256"]:
        raise ValueError("Current specification differs from the one used by the final run")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    metrics = json.loads((final_run / "metrics.json").read_text(encoding="utf-8"))
    predictions = pd.read_parquet(final_run / "predictions.parquet")
    reliability = pd.read_parquet(final_run / "reliability_bins.parquet")
    balanced_threshold = float(spec["policies"]["balanced"])
    balanced_matrix = metrics["subsets"]["official_dev"]["policies"]["balanced"]["confusion_matrix"]
    artifacts = []
    artifacts += save_figure(reliability_figure(reliability), output_dir, "reliability_final")
    artifacts += save_figure(risk_coverage_figure(predictions), output_dir, "risk_coverage_final")
    artifacts += save_figure(
        confusion_figure(balanced_matrix), output_dir, "confusion_balanced_final"
    )
    artifacts += save_figure(
        scenario_figure(predictions), output_dir, "scenario_probabilities_final"
    )

    subsets, retrieval, bootstrap = summary_tables(metrics)
    for name, frame in (
        ("subset_metrics.csv", subsets),
        ("retrieval_metrics.csv", retrieval),
        ("bootstrap_comparisons.csv", bootstrap),
        ("error_analysis_balanced.csv", error_analysis(predictions, balanced_threshold)),
    ):
        path = output_dir / name
        frame.to_csv(path, index=False)
        artifacts.append(path)

    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(Path.cwd().resolve()),
        "scope": "frozen_final_test_reporting",
        "source_run_id": source_manifest["run_id"],
        "frozen_spec_sha256": source_manifest["frozen_spec_sha256"],
        "predetermined_outputs": spec["reporting"],
        "final_test_used": True,
        "no_refit_or_recalibration": True,
        "sources": {
            "final_manifest": sha256_file(source_manifest_path),
            "metrics": sha256_file(final_run / "metrics.json"),
            "predictions": sha256_file(final_run / "predictions.parquet"),
        },
        "artifacts": {path.name: sha256_file(path) for path in artifacts},
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"OUTPUT_DIR={output_dir}")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
