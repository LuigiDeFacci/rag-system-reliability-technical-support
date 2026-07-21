# Diário de execução da pesquisa

## 2026-07-20 — especificação e dados

1. O DOCX do TCC foi lido sem alteração; pergunta, hipótese e recorte foram transcritos para
   `research_protocol.md`.
2. O release oficial do TechQA foi baixado em `data/raw/TechQA.tar.gz` e validado por tamanho
   e SHA-256. Somente o núcleo necessário foi extraído.
3. Esquema, licença, splits, spans, candidatos e duplicatas foram auditados. Problemas foram
   registrados em `data_quality_issues.md` e no manifesto local.
4. O treino oficial foi separado por grupos em `fit`, `calibration` e `selection`; o
   desenvolvimento oficial foi bloqueado como `final_test`.
5. O BM25 documental preliminar foi executado somente nos três splits internos.

## 2026-07-20 — recuperação por chunks

1. Foi criada uma `.venv` Python 3.10.2. O `pip` antigo falhou ao validar o certificado do
   PyPI; ele foi atualizado uma única vez com hosts confiáveis. Depois disso, TLS normal foi
   restaurado.
2. Chamadas Python ao Hugging Face também não enxergaram a cadeia do Windows. `truststore`
   foi incorporado para usar o repositório de certificados do sistema, sem desligar SSL.
3. O modelo `BAAI/bge-small-en-v1.5` foi fixado por revisão e licença. O cache local fica em
   `data/interim/model_cache`.
4. A primeira geração de chunks acumulava registros em RAM. Ao detectar menos de 1 GB livre,
   o processo foi interrompido e o escritor foi alterado para lotes Parquet. A execução já
   estava terminando e produziu um artefato íntegro com manifesto e hash: 90.284 chunks,
   28.461 documentos e máximo de 510 tokens.
5. A auditoria interna encontrou 438/450 spans integralmente contidos em um chunk. A união de
   intervalos no contexto top-k foi implementada para spans longos ou em fronteiras.
6. O benchmark CPU atingiu 4,77 chunks/s. Foi baixada a wheel oficial PyTorch CUDA 12.8 de
   2,75 GB; a GTX 1650 foi reconhecida e o benchmark subiu para 43,57 chunks/s.
7. Foram implementados ranking semântico exato, BM25 no mesmo corpus de chunks e fusão RRF.
   A codificação completa terminou em 38min12s e passou nas verificações de norma, finitude,
   alinhamento e hashes.
8. Após o commit local `9d88d73`, BM25, semântico e RRF foram executados nas 600 perguntas
   internas. Os três runs passaram na auditoria de artefatos; nenhum acessou o teste final.

Cada resultado científico posterior deve acrescentar `run_id`, configuração, hashes, métricas
e decisão decorrente neste diário ou no `experiment_registry.md`.
