# Confiabilidade de evidência em sistemas RAG

Repositório de pesquisa do TCC sobre decisão seletiva em sistemas RAG para suporte técnico. O objetivo é estimar, antes da geração, se o contexto recuperado contém evidência documental suficiente para autorizar uma resposta.

## Estado atual

O TechQA foi auditado e preparado. BM25, recuperação semântica, RRF, regressão logística,
calibração e robustez foram executados apenas nos splits internos e estão documentados como
resultados preliminares. O próximo passo é auditar negativos difíceis; o teste final permanece
bloqueado. O protocolo v1 está congelado e a campanha final possui plano separado.

## Estrutura

- `configs/`: configurações versionadas de dados, recuperação e experimentos.
- `data/`: instruções para dados locais; dados brutos e derivados não serão publicados sem licença compatível.
- `docs/`: protocolo, auditoria, decisões e texto-base para o TCC.
- `notebooks/`: auditoria e visualização; a implementação reutilizável ficará em `src/`.
- `src/rag_confidence/`: código da pesquisa organizado por etapa.
- `tests/`: verificações de dados, vazamento e reprodutibilidade.
- `results/runs/`: artefatos imutáveis por execução.

## Princípios científicos

- O rótulo depende da presença da evidência anotada, nunca das pontuações usadas como variáveis.
- Todas as variações da mesma pergunta permanecem no mesmo split.
- Calibração, seleção de limiar e teste usam dados separados.
- O teste final permanece bloqueado até o congelamento do protocolo.
- Negativos artificiais são análises de estresse, não substitutos silenciosos da distribuição natural.
- Resultados negativos ou equivalentes aos baselines serão reportados integralmente.

## Ambiente

Use Python 3.10 a 3.12. No host atual, a pesquisa está isolada em `.venv` com Python 3.10.2 porque o PyTorch no Windows não suporta o Python 3.14 instalado como padrão. JupyterLab, testes e lint estão disponíveis na própria `.venv`.

`requirements-win-cuda.lock.txt` reproduz o ambiente validado neste host (Windows,
Python 3.10 e CUDA 12.8). Em outro sistema, use o `pyproject.toml` e gere um lock específico
da plataforma; wheels do PyTorch não são portáveis entre CPU, CUDA e sistemas operacionais.

## Dados

Não adicione o TechQA ou o corpus de Technotes ao Git sem confirmar os termos de uso. Consulte `data/README.md` e `docs/data_audit.md`. Credenciais devem existir apenas em `.env`, que é ignorado pelo Git.

## Comandos atuais

```powershell
powershell -ExecutionPolicy Bypass -Command "py -3.10 -m venv .venv"
.\.venv\Scripts\python.exe -m pip install -e ".[retrieval,dev,notebooks]"
powershell -ExecutionPolicy Bypass -File scripts/download_techqa.ps1
powershell -ExecutionPolicy Bypass -File scripts/extract_techqa_core.ps1
$env:PYTHONPATH = (Resolve-Path .\src).Path
.\.venv\Scripts\python.exe -m rag_confidence.data.audit
.\.venv\Scripts\python.exe -m rag_confidence.data.prepare
.\.venv\Scripts\python.exe -m rag_confidence.retrieval.run_bm25
.\.venv\Scripts\python.exe -m rag_confidence.retrieval.build_chunks
.\.venv\Scripts\python.exe -m rag_confidence.scenarios.build_natural --help
.\.venv\Scripts\python.exe -m rag_confidence.features.build --help
.\.venv\Scripts\python.exe -m rag_confidence.models.train_internal --help
.\.venv\Scripts\python.exe -m rag_confidence.evaluation.run_robustness --help
.\.venv\Scripts\python.exe -m rag_confidence.scenarios.build_hard_negatives --help
.\.venv\Scripts\python.exe -m rag_confidence.evaluation.evaluate_hard_negatives --help
.\.venv\Scripts\python.exe -m rag_confidence.evaluation.run_prevalence_sensitivity --help
.\.venv\Scripts\python.exe -m rag_confidence.reporting.generate_internal_report --help
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests
```

O download é retomável e validado por tamanho e SHA-256. A extração padrão inclui apenas os arquivos necessários à análise principal; não expande as representações redundantes do corpus integral.

## Documentos principais

- Protocolo provisório: `docs/research_protocol.md`
- Revisão das instruções recebidas: `docs/instruction_review.md`
- Estado da auditoria: `docs/data_audit.md`
- Questões de qualidade: `docs/data_quality_issues.md`
- Preparação canônica: `docs/data_preparation.md`
- Baseline lexical: `docs/bm25_baseline.md`
- Recuperação semântica: `docs/semantic_retrieval.md`
- Resultados internos de retrieval: `docs/retrieval_results_internal.md`
- Confiança e robustez internas: `docs/confidence_results_internal.md`
- Auditoria de negativos difíceis: `docs/hard_negative_audit.md`
- Sensibilidade à prevalência: `docs/prevalence_sensitivity.md`
- Plano congelado do teste: `docs/final_test_plan.md`
- Registro de acesso ao holdout: `docs/test_access_log.md`
- Diário cronológico: `docs/development_log.md`
- Decisões metodológicas: `docs/decisions.md`
- Registro de experimentos: `docs/experiment_registry.md`
- Resultados para transcrição: `docs/tcc_results_draft.md`
