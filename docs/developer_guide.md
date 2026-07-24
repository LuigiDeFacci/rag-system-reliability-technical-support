# Guia técnico para colaboradores

## Ambiente

Use a versão do Python compatível com `pyproject.toml` e instale o projeto em
modo editável:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[retrieval,dev,notebooks]"
$env:PYTHONPATH = (Resolve-Path .\src).Path
```

## Fluxo de execução

Os comandos devem ser executados nesta ordem: auditoria, preparação,
segmentação, recuperação, cenários, features, ajuste interno, calibração,
relatórios e, somente quando autorizado, teste final. O `README.md` lista os
comandos de cada etapa; `docs/code_walkthrough.md` explica o papel de cada
módulo.

## Como documentar uma mudança

Toda alteração deve explicar no próprio commit ou em `docs/decisions.md`:

1. qual pergunta científica é afetada;
2. quais arquivos de entrada e saída mudam;
3. se a mudança pode introduzir vazamento;
4. como os testes foram executados;
5. se o protocolo congelado permanece válido.

Comentários devem explicar decisões ou invariantes, não repetir literalmente o
código. Funções públicas devem ter docstring com propósito, entradas, saídas e
erros esperados.

## Verificações antes de publicar

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests
```

Não publique chaves, `.env`, dados sem licença de redistribuição, embeddings
grandes ou artefatos temporários. Resultados experimentais devem ficar em um
diretório próprio de `run_id` e nunca ser sobrescritos.

## Notebooks

Cada notebook deve declarar no início quais artefatos lê, qual pergunta ajuda a
responder e se produz arquivos. Células de treinamento ou alteração de dados
não pertencem aos notebooks de resultados congelados. A convenção e o papel de
cada notebook estão em `docs/notebooks_guide.md`.
