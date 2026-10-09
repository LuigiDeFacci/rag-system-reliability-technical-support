# Evidence Reliability in RAG Systems

Research repository for an MBA capstone project on selective prediction in RAG systems for technical support. The goal is to estimate, before generation, whether the retrieved context contains the annotated documentary evidence required to authorize an answer.

**Author:** Luigi De Facci · [ORCID: 0009-0006-3250-2875](https://orcid.org/0009-0006-3250-2875)

**Related preprint:** *When Should RAG Abstain? Predicting Document Sufficiency Before Generation* · [DOI: 10.5281/zenodo.23267442](https://doi.org/10.5281/zenodo.23267442)

## Current status

The TechQA audit and data preparation are complete. BM25, semantic retrieval, reciprocal rank fusion (RRF), logistic regression, calibration, robustness analyses, and the frozen final evaluation have been completed. The official development partition served as the local final holdout, rather than the original blind test set, without refitting or recalibration during that evaluation. The final-evaluation gate is closed again. The hypothesis received partial support; limitations and inconclusive findings are reported in full.

For reading alongside the preprint, start with the [final results](docs/final_results.md), the [research questions and evidence matrix](docs/research_questions_evidence_matrix.md), and the [tables and figures](figures/README.md). Risk reductions relative to RRF at coverage levels up to 40% were descriptive: paired confidence intervals include zero. Internally selected thresholds also failed to maintain their intended risk levels on the holdout.

## Repository structure

- `configs/`: versioned data, retrieval, and experiment settings.
- `data/`: local data instructions; redistribution requires compatible terms.
- `docs/`: protocol, audits, decisions, and capstone documentation.
- `notebooks/`: audits and visualizations using reusable code in `src/`.
- `src/rag_confidence/`: research code organized by pipeline stage.
- `tests/`: checks for data integrity, leakage, and reproducibility.
- `results/runs/`: immutable artifacts for each run.

Complete run outputs and source data must be obtained or generated locally. Versioned tables, figures, and summaries support checking the reported numbers without redistributing the corpus. Supporting research documents are currently primarily in Portuguese.

## Research principles

- Labels depend on annotated evidence, never on the scores used as predictive features.
- Variants of the same question stay within the same internal split; train–holdout overlaps are documented and assessed separately.
- Calibration, threshold selection, and final evaluation use separate partitions.
- Final evaluation requires a frozen protocol and an explicitly authorized gate. Historical annotation access is recorded in the [holdout access log](docs/test_access_log.md).
- Artificial negatives are stress tests, not substitutes for the natural data distribution.
- Negative findings and results comparable to the baselines are reported in full.

## Environment

The declared Python range is 3.10–3.12. The historical experiment used Python 3.10.2 on Windows with CUDA 12.8. Create a local virtual environment before installing dependencies.

`requirements-win-cuda.lock.txt` records the historical environment. On another platform, use `pyproject.toml` and resolve compatible dependencies; PyTorch wheels depend on the operating system and CPU/CUDA configuration.

A subsequent partial reproduction with Python 3.14 reproduced data preparation, feature extraction from saved rankings, and model fitting to numerical precision. It did not rerun the complete embedding and retrieval pipeline or establish full Python 3.14 compatibility. A clean-environment, end-to-end reproduction remains unverified.

## Data

Before adding TechQA or the Technote corpus to Git, check the applicable redistribution terms. See [data instructions](data/README.md) and the [data audit](docs/data_audit.md). Store credentials only in `.env`, which Git ignores.

## License and citation

The original code, documentation, tables, and figures versioned in this repository are distributed under the [Apache License 2.0](LICENSE), copyright 2026 Luigi De Facci. This license does not extend to TechQA, Technotes, third-party publications, or external models; each retains its own terms.

For the accompanying study, cite:

> De Facci, Luigi. *When Should RAG Abstain? Predicting Document Sufficiency Before Generation*. Zenodo preprint. https://doi.org/10.5281/zenodo.23267442

This DOI identifies the preprint. When referring to the implementation, also identify the repository commit or tag corresponding to the results used. Machine-readable metadata is provided in [CITATION.cff](CITATION.cff).

## Commands

```powershell
powershell -ExecutionPolicy Bypass -Command "py -3.10 -m venv .venv"
.\.venv\Scripts\python.exe -m pip install -e ".[retrieval,dev,notebooks]"
powershell -ExecutionPolicy Bypass -File scripts/download_techqa.ps1
powershell -ExecutionPolicy Bypass -File scripts/extract_techqa_core.ps1
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m rag_confidence.data.audit
.\.venv\Scripts\python.exe -m rag_confidence.data.prepare
.\.venv\Scripts\python.exe -m rag_confidence.retrieval.build_chunks
.\.venv\Scripts\python.exe -m rag_confidence.retrieval.build_embeddings
.\.venv\Scripts\python.exe -m rag_confidence.retrieval.run_chunk_bm25
.\.venv\Scripts\python.exe -m rag_confidence.retrieval.run_semantic
.\.venv\Scripts\python.exe -m rag_confidence.retrieval.run_hybrid --help
.\.venv\Scripts\python.exe -m rag_confidence.scenarios.build_natural --help
.\.venv\Scripts\python.exe -m rag_confidence.features.build --help
.\.venv\Scripts\python.exe -m rag_confidence.models.train_internal --help
.\.venv\Scripts\python.exe -m rag_confidence.evaluation.run_robustness --help
.\.venv\Scripts\python.exe -m rag_confidence.scenarios.build_hard_negatives --help
.\.venv\Scripts\python.exe -m rag_confidence.evaluation.evaluate_hard_negatives --help
.\.venv\Scripts\python.exe -m rag_confidence.evaluation.run_prevalence_sensitivity --help
.\.venv\Scripts\python.exe -m rag_confidence.evaluation.run_fixed_coverage_risk --help
.\.venv\Scripts\python.exe -m rag_confidence.reporting.generate_internal_report --help
.\.venv\Scripts\python.exe -m rag_confidence.reporting.generate_fixed_coverage_report --help
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests
```

The first two data commands audit and prepare local files. Chunking and embeddings precede lexical and semantic ranking. RRF requires the paths of both retrieval runs through `--bm25-run` and `--semantic-run`; consult `--help` for the required arguments.

Scenario construction assigns labels, while feature extraction builds predictive inputs without including those labels. Internal training fits and calibrates the model without opening the holdout. Reporting commands read existing artifacts. Final evaluation is a separate, controlled stage and should not be used for exploratory tuning.

For the purpose of each stage, see the [code walkthrough](docs/code_walkthrough.md). For contributions to code comments, tests, or documentation, follow the [developer guide](docs/developer_guide.md). Notebooks and their data sources are described in the [notebook guide](docs/notebooks_guide.md).

The download supports resuming and validates file size and SHA-256. By default, extraction includes only the files needed for the main analysis, without expanding redundant representations of the full corpus.

## Key documents

- Research protocol: `docs/research_protocol.md`
- Review of project instructions: `docs/instruction_review.md`
- Data audit: `docs/data_audit.md`
- Data-quality issues: `docs/data_quality_issues.md`
- Canonical data preparation: `docs/data_preparation.md`
- Lexical baseline: `docs/bm25_baseline.md`
- Semantic retrieval: `docs/semantic_retrieval.md`
- Internal retrieval results: `docs/retrieval_results_internal.md`
- Internal confidence and robustness: `docs/confidence_results_internal.md`
- Hard-negative audit: `docs/hard_negative_audit.md`
- Prevalence sensitivity: `docs/prevalence_sensitivity.md`
- Risk at fixed coverage: `docs/fixed_coverage_risk.md`
- Frozen final-evaluation plan: `docs/final_test_plan.md`
- Final results: `docs/final_results.md`
- Research questions and evidence matrix: `docs/research_questions_evidence_matrix.md`
- Chapters 8–10 checklist: `docs/chapters_8_10_replacement_checklist.md`
- Holdout access log: `docs/test_access_log.md`
- Development log: `docs/development_log.md`
- Methodological decisions: `docs/decisions.md`
- Experiment registry: `docs/experiment_registry.md`
- Results for manuscript preparation: `docs/tcc_results_draft.md`
- Public-release guide: `docs/public_release.md`

## Releases and future publications

The public repository does not distribute the TechQA corpus, embeddings, serialized models, or reference-library PDFs. The download script and checksums support local data preparation under the applicable terms.

Before publishing a release, follow the [release guide](docs/public_release.md) and run `scripts/check_public_release.ps1`. Future publications should cite a stable commit or tag and identify the `run_id` and hashes of the artifacts used.
