# Guia de publicação do repositório

Este repositório deve ser publicado como um artefato de pesquisa reproduzível,
não como um espelho do computador de trabalho.

## Pode ser publicado

- `src/`, `scripts/`, `configs/`, `tests/` e `pyproject.toml`;
- `README.md`, `AGENTS.md`, `CITATION.cff` e documentação em `docs/`;
- notebooks que apenas leem artefatos e produzem visualizações;
- figuras e tabelas finais pequenas, acompanhadas de manifesto e origem;
- resumos de auditoria e resultados sem conteúdo integral do corpus.

## Não publicar

- `data/raw/`, `data/interim/` e `data/processed/` com o TechQA, chunks,
  embeddings ou caches de modelos;
- modelos serializados, rankings completos e artefatos grandes de execução;
- PDFs de artigos cuja redistribuição não esteja autorizada;
- TCCs em `.docx`, PDFs de conferência e materiais internos do curso;
- `.env`, chaves, tokens, credenciais ou caminhos locais do computador.

O TechQA deve ser obtido pelo script autorizado e verificado por SHA-256. A
licença e os limites de redistribuição estão documentados em
`docs/data_audit.md` e `data/README.md`.

## Checagem antes do primeiro push

```powershell
git status --short
git ls-files | Select-String -Pattern '\.(tar\.gz|parquet|npy|safetensors|joblib|docx|pdf)$'
rg -n --hidden --glob '!\.git/**' --glob '!.venv/**' '(sk-[A-Za-z0-9]|AIza|BEGIN PRIVATE KEY|api[_-]?key|password)' .
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
```

## Para artigos futuros

Cada artigo deve apontar para uma tag ou commit estável e declarar a versão do
dataset, o protocolo, o `run_id`, o modelo de embeddings e os hashes dos
artefatos. Resultados novos devem ser gravados em outro diretório de execução;
eles não devem substituir os resultados congelados do TCC.
