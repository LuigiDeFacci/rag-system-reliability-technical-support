"""Build auditable non-gold top-ranked contexts for stress testing.

The gold document is removed before selecting non-gold chunks. These contexts
are internal stress tests and never replace the natural holdout distribution.

The label means absence of the annotated gold evidence. It does not claim that every
non-gold Technote is globally irrelevant or that unannotated equivalent evidence is absent.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from rag_confidence.data.audit import sha256_file
from rag_confidence.features.build import CODE_PATTERN, VERSION_PATTERN
from rag_confidence.retrieval.rrf import reciprocal_rank_fusion
from rag_confidence.retrieval.run_bm25 import git_commit
from rag_confidence.retrieval.run_hybrid import chunks_from_row

CVE_PATTERN = re.compile(r"(?i)\bCVE-\d{4}-\d+\b")


def normalized_patterns(pattern: Any, text: str) -> set[str]:
    return {value.casefold().replace(" ", "") for value in pattern.findall(text)}


def conflict_note(query_text: str, context_text: str) -> str | None:
    notes = []
    for label, pattern in (("version", VERSION_PATTERN), ("code", CODE_PATTERN)):
        query_values = normalized_patterns(pattern, query_text)
        context_values = normalized_patterns(pattern, context_text)
        if query_values and context_values and query_values.isdisjoint(context_values):
            notes.append(
                f"{label}:query={','.join(sorted(query_values))};"
                f"context={','.join(sorted(context_values))}"
            )
    return " | ".join(notes) if notes else None


def top_non_gold_context(ranking: pd.Series, gold_document_id: str, cutoff: int) -> dict[str, Any]:
    selected = []
    for rank, (chunk_id, document_id, score) in enumerate(
        zip(
            ranking["ranked_chunk_ids"],
            ranking["ranked_chunk_document_ids"],
            ranking["ranked_chunk_scores"],
            strict=True,
        ),
        start=1,
    ):
        if str(document_id) == gold_document_id:
            continue
        selected.append(
            {
                "chunk_id": str(chunk_id),
                "document_id": str(document_id),
                "score": float(score),
                "source_rank": rank,
            }
        )
        if len(selected) == cutoff:
            break
    if len(selected) != cutoff:
        raise ValueError("Ranking does not contain enough non-gold chunks")
    return {
        "included_chunk_ids": [row["chunk_id"] for row in selected],
        "included_document_ids": list(dict.fromkeys(row["document_id"] for row in selected)),
        "included_chunk_scores": [row["score"] for row in selected],
        "source_chunk_ranks": [row["source_rank"] for row in selected],
    }


def filter_gold_ranking(ranking: pd.Series, gold_document_id: str) -> pd.Series:
    """Return a full ranking with every chunk from the gold document removed."""
    positions = [
        index
        for index, document_id in enumerate(ranking["ranked_chunk_document_ids"])
        if str(document_id) != gold_document_id
    ]
    result = ranking.copy()
    for column in (
        "ranked_chunk_ids",
        "ranked_chunk_document_ids",
        "ranked_chunk_scores",
        "ranked_chunk_body_starts",
        "ranked_chunk_body_ends",
    ):
        result[column] = [ranking[column][index] for index in positions]
    result["candidate_chunk_count"] = len(positions)
    return result


def fuse_filtered_rankings(lexical: pd.Series, semantic: pd.Series, rrf_k: int = 60) -> pd.Series:
    fused, _ = reciprocal_rank_fusion(
        chunks_from_row(lexical), chunks_from_row(semantic), rrf_k=rrf_k
    )
    return pd.Series(
        {
            "ranked_chunk_ids": [item.chunk_id for item in fused],
            "ranked_chunk_document_ids": [item.document_id for item in fused],
            "ranked_chunk_scores": [item.score for item in fused],
            "ranked_chunk_body_starts": [item.body_start_char for item in fused],
            "ranked_chunk_body_ends": [item.body_end_char for item in fused],
            "candidate_chunk_count": len(fused),
        }
    )


def build_records(
    questions: pd.DataFrame,
    rankings: dict[str, pd.DataFrame],
    chunks: pd.DataFrame,
    documents: pd.DataFrame,
    *,
    cutoff: int,
    seed: int,
    source_run_ids: dict[str, str],
    code_commit: str | None,
) -> list[dict[str, Any]]:
    ranking_maps = {name: frame.set_index("query_id") for name, frame in rankings.items()}
    chunk_text = chunks.set_index("chunk_id")["passage_text"].astype(str).to_dict()
    document_rows = documents.set_index("document_id")
    records = []
    answerable = questions[questions["answerable"].astype(bool)]
    for question in answerable.itertuples(index=False):
        query_id = str(question.query_id)
        gold_document_id = str(question.gold_document_id)
        gold_product = str(document_rows.loc[gold_document_id, "product_name"])
        filtered = {
            method: filter_gold_ranking(ranking_maps[method].loc[query_id], gold_document_id)
            for method in ("bm25", "semantic")
        }
        filtered["hybrid"] = fuse_filtered_rankings(filtered["bm25"], filtered["semantic"])
        for method in ("bm25", "semantic", "hybrid"):
            context = top_non_gold_context(filtered[method], gold_document_id, cutoff)
            if gold_document_id in context["included_document_ids"]:
                raise AssertionError("Gold document leaked into a hard-negative context")
            context_body = "\n".join(chunk_text[value] for value in context["included_chunk_ids"])
            technical_conflict = conflict_note(str(question.query_text), context_body)
            query_cves = normalized_patterns(CVE_PATTERN, str(question.query_text))
            context_cves = normalized_patterns(CVE_PATTERN, context_body)
            same_gold_product = any(
                str(document_rows.loc[document_id, "product_name"]) == gold_product
                for document_id in context["included_document_ids"]
            )
            confirmed_cve_conflict = bool(
                same_gold_product
                and query_cves
                and context_cves
                and query_cves.isdisjoint(context_cves)
            )
            retrieved_products = sorted(
                {
                    str(document_rows.loc[document_id, "product_name"])
                    for document_id in context["included_document_ids"]
                    if str(document_rows.loc[document_id, "product_name"]) != gold_product
                }
            )
            product_note = (
                f"gold={gold_product};retrieved={' | '.join(retrieved_products)}"
                if retrieved_products
                else None
            )
            if confirmed_cve_conflict:
                scenario_type = f"confirmed_cve_conflict_{method}"
                conflict_status = "exact_cve_mismatch_with_same_product"
            elif technical_conflict and same_gold_product:
                scenario_type = f"technical_conflict_candidate_{method}"
                conflict_status = "heuristic_candidate_requires_manual_review"
            else:
                scenario_type = f"hard_{method}_non_gold"
                conflict_status = "not_classified_as_technical_conflict"
            records.append(
                {
                    "scenario_id": f"{query_id}__hard_{method}_k{cutoff}",
                    "query_id": query_id,
                    "research_split": str(question.research_split),
                    "context_k": cutoff,
                    "scenario_family": "constructed_hard_negative",
                    "scenario_type": scenario_type,
                    "evidence_sufficient": False,
                    "relevant_document_id": gold_document_id,
                    "removed_document_ids": [gold_document_id],
                    **context,
                    "classification_reason": (
                        "annotated gold document excluded before selecting top-ranked chunks"
                    ),
                    "conflicting_product": product_note,
                    "conflicting_version_or_code": technical_conflict,
                    "same_gold_product_in_context": same_gold_product,
                    "conflict_detection_status": conflict_status,
                    "negative_selection_method": (
                        f"top_{cutoff}_{method}_chunks_after_gold_document_exclusion"
                    ),
                    "seed": seed,
                    "source_run_id": source_run_ids.get(
                        method,
                        f"derived_rrf:{source_run_ids['bm25']}+{source_run_ids['semantic']}",
                    ),
                    "code_commit": code_commit,
                }
            )
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bm25-run", type=Path, required=True)
    parser.add_argument("--semantic-run", type=Path, required=True)
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/techqa_v1"))
    parser.add_argument("--chunks-dir", type=Path, default=Path("data/interim/chunks_bge_v1"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/interim/scenarios_hard_v1"))
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.k <= 0:
        raise ValueError("k must be positive")
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite scenarios: {output_dir}")
    run_paths = {"bm25": args.bm25_run.resolve(), "semantic": args.semantic_run.resolve()}
    manifests = {
        name: json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        for name, path in run_paths.items()
    }
    if any(manifest["final_test_used"] for manifest in manifests.values()):
        raise PermissionError("Hard-negative builder refuses final-test source runs")
    rankings = {
        name: pd.read_parquet(path / "rankings.parquet") for name, path in run_paths.items()
    }
    processed_dir = args.processed_dir.resolve()
    chunks_dir = args.chunks_dir.resolve()
    questions_path = processed_dir / "questions.parquet"
    documents_path = processed_dir / "documents.parquet"
    chunks_path = chunks_dir / "chunks.parquet"
    internal_ids = set(rankings["bm25"]["query_id"])
    questions = pd.read_parquet(questions_path)
    questions = questions[questions["query_id"].isin(internal_ids)].copy()
    if set(questions["query_id"]) != set(rankings["semantic"]["query_id"]):
        raise ValueError("BM25 and semantic runs contain different query IDs")
    records = build_records(
        questions,
        rankings,
        pd.read_parquet(chunks_path),
        pd.read_parquet(documents_path),
        cutoff=args.k,
        seed=args.seed,
        source_run_ids={name: str(manifest["run_id"]) for name, manifest in manifests.items()},
        code_commit=git_commit(Path.cwd().resolve()),
    )
    scenarios = pd.DataFrame(records)
    if scenarios["evidence_sufficient"].any():
        raise AssertionError("A hard-negative scenario received a positive label")
    if any(
        row.relevant_document_id in row.included_document_ids
        for row in scenarios.itertuples(index=False)
    ):
        raise AssertionError("A hard-negative scenario contains its gold document")
    output_dir.mkdir(parents=True, exist_ok=False)
    scenarios_path = output_dir / "scenarios.parquet"
    scenarios.to_parquet(scenarios_path, index=False, compression="zstd")
    counts = (
        scenarios.groupby(["research_split", "scenario_type"], sort=True)
        .size()
        .rename("rows")
        .reset_index()
        .to_dict(orient="records")
    )
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "version": "hard_negatives_v1",
        "scope": "internal_only",
        "label_definition": "absence_of_annotated_gold_document",
        "unannotated_equivalent_evidence_possible": True,
        "manual_conflict_review_required": True,
        "code_commit": git_commit(Path.cwd().resolve()),
        "seed": args.seed,
        "context_k": args.k,
        "rows": int(len(scenarios)),
        "unique_queries": int(scenarios["query_id"].nunique()),
        "counts": counts,
        "source_runs": {
            name: {
                "run_id": manifests[name]["run_id"],
                "rankings_sha256": sha256_file(path / "rankings.parquet"),
            }
            for name, path in run_paths.items()
        },
        "sources": {
            "questions_sha256": sha256_file(questions_path),
            "documents_sha256": sha256_file(documents_path),
            "chunks_sha256": sha256_file(chunks_path),
        },
        "scenarios_sha256": sha256_file(scenarios_path),
        "final_test_used": False,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
