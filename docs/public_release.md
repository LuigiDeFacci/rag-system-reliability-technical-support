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

O manuscrito local e a biblioteca `Referemcoas/` ficam fora do Git; o preprint deve
apontar para o repositório de código e resultados públicos. O conteúdo original
versionado está sob [Apache License 2.0](../LICENSE). O TechQA e os artigos citados
mantêm suas próprias licenças; a licença deste repositório não os substitui.

O TechQA deve ser obtido pelo script autorizado e verificado por SHA-256. A
licença e os limites de redistribuição estão documentados em
`docs/data_audit.md` e `data/README.md`.

## Checagem antes do primeiro push

```powershell
git status --short
.\scripts\check_public_release.ps1
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
```

O verificador examina arquivos atualmente rastreados no diretório de trabalho: extensões,
tamanho, diretórios locais e padrões comuns de segredo ou caminho pessoal em arquivos de
texto. Ele não prova ausência de dados sensíveis em conteúdo binário nem no histórico.
Antes de tornar o repositório público, revise também os nomes no histórico com
`git rev-list --objects --all` e confirme que a tag/commit citado no preprint corresponde
aos resultados e manifestos publicados. Se um segredo tiver sido versionado no passado,
revogue-o antes de tratar a reescrita do histórico.

## Para artigos futuros

Cada artigo deve apontar para uma tag ou commit estável e declarar a versão do
dataset, o protocolo, o `run_id`, o modelo de embeddings e os hashes dos
artefatos. Resultados novos devem ser gravados em outro diretório de execução;
eles não devem substituir os resultados congelados do TCC.
