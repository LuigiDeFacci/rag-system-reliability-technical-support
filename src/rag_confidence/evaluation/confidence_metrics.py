"""Classification, calibration and selective-decision metrics."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def reliability_bins(
    y_true: np.ndarray, probabilities: np.ndarray, n_bins: int = 10
) -> list[dict[str, Any]]:
    if n_bins <= 0:
        raise ValueError("n_bins must be positive")
    y = np.asarray(y_true, dtype=np.int64)
    p = np.asarray(probabilities, dtype=np.float64)
    if len(y) != len(p) or not len(y):
        raise ValueError("Labels and probabilities must have the same non-zero length")
    if np.any((p < 0) | (p > 1)):
        raise ValueError("Probabilities must be in [0, 1]")
    indices = np.minimum((p * n_bins).astype(int), n_bins - 1)
    rows = []
    for bin_index in range(n_bins):
        mask = indices == bin_index
        count = int(mask.sum())
        rows.append(
            {
                "bin": bin_index,
                "lower": bin_index / n_bins,
                "upper": (bin_index + 1) / n_bins,
                "count": count,
                "mean_confidence": None if not count else float(p[mask].mean()),
                "fraction_positive": None if not count else float(y[mask].mean()),
            }
        )
    return rows


def expected_calibration_error(
    y_true: np.ndarray, probabilities: np.ndarray, n_bins: int = 10
) -> tuple[float, list[dict[str, Any]]]:
    bins = reliability_bins(y_true, probabilities, n_bins)
    total = len(y_true)
    ece = sum(
        row["count"] / total * abs(float(row["mean_confidence"]) - float(row["fraction_positive"]))
        for row in bins
        if row["count"]
    )
    return float(ece), bins


def classification_metrics(
    y_true: np.ndarray, scores: np.ndarray, threshold: float
) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=np.int64)
    values = np.asarray(scores, dtype=np.float64)
    predicted = values >= threshold
    matrix = confusion_matrix(y, predicted, labels=[0, 1])
    coverage = float(predicted.mean())
    selective_risk = 0.0 if not predicted.any() else float((1 - y[predicted]).mean())
    return {
        "threshold": float(threshold),
        "coverage": coverage,
        "selective_risk": selective_risk,
        "precision": float(precision_score(y, predicted, zero_division=0)),
        "recall": float(recall_score(y, predicted, zero_division=0)),
        "f1": float(f1_score(y, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, values)),
        "pr_auc": float(average_precision_score(y, values)),
        "confusion_matrix": matrix.astype(int).tolist(),
    }


def best_f1_threshold(y_true: np.ndarray, scores: np.ndarray) -> dict[str, Any]:
    values = np.asarray(scores, dtype=np.float64)
    candidates = [float(np.nextafter(values.max(), np.inf)), *np.unique(values).tolist()]
    evaluated = [classification_metrics(y_true, values, threshold) for threshold in candidates]
    return max(
        evaluated,
        key=lambda row: (row["f1"], row["precision"], row["threshold"]),
    )


def selective_curve(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    y = np.asarray(y_true, dtype=np.int64)
    p = np.asarray(probabilities, dtype=np.float64)
    order = np.argsort(-p, kind="stable")
    errors = 1 - y[order]
    accepted = np.arange(1, len(y) + 1)
    coverage = accepted / len(y)
    risk = np.cumsum(errors) / accepted
    return {
        "coverage": coverage.tolist(),
        "risk": risk.tolist(),
        "threshold": p[order].tolist(),
        "aurc_discrete": float(risk.mean()),
    }


def threshold_for_maximum_coverage_at_risk(
    y_true: np.ndarray, probabilities: np.ndarray, maximum_risk: float
) -> dict[str, float]:
    if not 0 <= maximum_risk <= 1:
        raise ValueError("maximum_risk must be in [0, 1]")
    y = np.asarray(y_true, dtype=np.int64)
    p = np.asarray(probabilities, dtype=np.float64)
    candidates = [float(np.nextafter(p.max(), np.inf)), *np.unique(p).tolist()]
    feasible = []
    for threshold in candidates:
        accepted = p >= threshold
        coverage = float(accepted.mean())
        risk = 0.0 if not accepted.any() else float((1 - y[accepted]).mean())
        if risk <= maximum_risk:
            feasible.append({"threshold": threshold, "coverage": coverage, "risk": risk})
    return max(feasible, key=lambda row: (row["coverage"], row["threshold"]))


def selective_summary(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    curve = selective_curve(y_true, probabilities)
    y = np.asarray(y_true, dtype=np.int64)
    p = np.asarray(probabilities, dtype=np.float64)
    risk_at_coverage = {}
    order = np.argsort(-p, kind="stable")
    for target in (0.25, 0.50, 0.75, 1.0):
        accepted_count = max(1, int(math.ceil(target * len(y))))
        accepted = order[:accepted_count]
        risk_at_coverage[str(target)] = float((1 - y[accepted]).mean())
    coverage_at_risk = {
        str(target): threshold_for_maximum_coverage_at_risk(y, p, target)
        for target in (0.05, 0.10, 0.20)
    }
    return {
        "aurc_discrete": curve["aurc_discrete"],
        "risk_at_coverage": risk_at_coverage,
        "coverage_at_risk": coverage_at_risk,
        "curve": curve,
    }
