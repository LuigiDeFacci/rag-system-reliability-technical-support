"""Render the post-hoc fixed-coverage analysis as versioned tables and a figure."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from rag_confidence.data.audit import sha256_file
from rag_confidence.retrieval.run_bm25 import git_commit


METHOD_LABELS = {
    "logistic": "Logística",
    "bm25": "BM25 top-1",
    "semantic": "Semântico top-1",
    "rrf": "RRF top-1",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-run", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.analysis_run.resolve()
    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("posthoc_reporting_only"):
        raise PermissionError("Expected a post-hoc reporting run")
    if not manifest.get("no_refit_recalibration_or_threshold_selection"):
        raise PermissionError("The source analysis must not refit or select thresholds")
    if not manifest.get("gate_remained_locked"):
        raise PermissionError("The final holdout gate must have remained locked")

    source = pd.read_parquet(run_dir / "fixed_coverage_risk.parquet")
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    intervals = []
    for method, by_coverage in metrics["methods"].items():
        for coverage, values in by_coverage.items():
            intervals.append(
                {
                    "method": method,
                    "coverage": float(coverage),
                    "ci_lower": values["ci_lower"],
                    "ci_upper": values["ci_upper"],
                }
            )
    table = source.rename(columns={"target_coverage": "coverage"}).merge(
        pd.DataFrame(intervals), on=["method", "coverage"], validate="one_to_one"
    )
    table["method_label"] = table["method"].map(METHOD_LABELS)
    table = table[
        [
            "method",
            "method_label",
            "coverage",
            "risk",
            "ci_lower",
            "ci_upper",
            "accepted_mass",
            "boundary_score",
            "boundary_tie_count",
            "boundary_fraction",
        ]
    ].sort_values(["coverage", "method"])

    reductions = []
    for baseline, by_coverage in metrics["logistic_risk_reduction"].items():
        for coverage, values in by_coverage.items():
            reductions.append(
                {
                    "baseline": baseline,
                    "baseline_label": METHOD_LABELS[baseline],
                    "coverage": float(coverage),
                    **values,
                }
            )
    reductions_frame = pd.DataFrame(reductions).sort_values(["coverage", "baseline"])

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    table_path = output_dir / "fixed_coverage_risk.csv"
    reductions_path = output_dir / "fixed_coverage_risk_reductions.csv"
    table.to_csv(table_path, index=False)
    reductions_frame.to_csv(reductions_path, index=False)

    figure, axis = plt.subplots(figsize=(7.2, 5.2))
    for method in ("logistic", "bm25", "semantic", "rrf"):
        rows = table[table["method"] == method].sort_values("coverage")
        axis.plot(
            rows["coverage"],
            rows["risk"],
            marker="o",
            linewidth=2.2 if method == "logistic" else 1.5,
            label=METHOD_LABELS[method],
        )
    axis.set(
        xlabel="Cobertura fixada",
        ylabel="Risco seletivo",
        xlim=(0.08, 1.02),
        ylim=(0, 0.75),
    )
    axis.set_title("Risco em coberturas comparáveis — holdout final local")
    axis.grid(alpha=0.25)
    axis.legend(frameon=False)
    figure.tight_layout()
    png_path = output_dir / "fixed_coverage_risk.png"
    svg_path = output_dir / "fixed_coverage_risk.svg"
    figure.savefig(png_path, dpi=180, bbox_inches="tight")
    figure.savefig(svg_path, bbox_inches="tight")
    plt.close(figure)

    artifacts = [table_path, reductions_path, png_path, svg_path]
    report_manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(Path.cwd().resolve()),
        "source_run_id": manifest["run_id"],
        "source_manifest_sha256": sha256_file(manifest_path),
        "scope": "posthoc_reporting_from_frozen_predictions",
        "gate_remained_locked": True,
        "artifacts": {path.name: sha256_file(path) for path in artifacts},
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(report_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
