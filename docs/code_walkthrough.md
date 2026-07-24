# Guia de leitura do código

Este documento explica como o código implementa o protocolo descrito em
`docs/research_protocol.md`. A ordem abaixo é também a ordem recomendada para
ler ou reproduzir a pesquisa.

## 1. Entrada e auditoria

`scripts/download_techqa.ps1` baixa os arquivos autorizados e
`scripts/extract_techqa_core.ps1` extrai somente o subconjunto necessário.
`rag_confidence.data.audit` lê os arquivos locais sem alterá-los, calcula
hashes, verifica campos, alinhamento entre perguntas e referências e registra
os achados no manifesto da auditoria.

## 2. Preparação dos splits

`rag_confidence.data.prepare` deduplica candidatos preservando a ordem,
constrói a tabela canônica e divide apenas o treino em `fit`, `calibration` e
`selection`. A divisão é agrupada pelo fingerprint do texto da pergunta. O
desenvolvimento permanece reservado ao `final_test`; `validation` é apenas a
cópia oficial usada no smoke test estrutural.

## 3. Recuperação e contextos

`retrieval.chunking` e `retrieval.build_chunks` aplicam a segmentação congelada.
`retrieval.run_bm25`, `retrieval.run_semantic` e `retrieval.run_hybrid` geram
rankings sobre os candidatos oficiais. O módulo `retrieval.rrf` combina posições
sem somar scores incompatíveis.

## 4. Cenários e variáveis

`scenarios.build_natural` monta os contextos naturais. Os negativos difíceis
são construídos separadamente por `scenarios.build_hard_negatives` e nunca
substituem a distribuição principal. `features.build` extrai somente sinais
disponíveis antes da geração; campos gold, rótulos e tipo de cenário são
bloqueados por verificações explícitas.

## 5. Modelo e avaliação

`models.train_internal` ajusta a regressão logística, calibra em split separado
e escolhe políticas somente na validação interna. `evaluation.run_final_test`
é o único ponto que abre o holdout e exige uma autorização explícita. As
métricas, bootstrap agrupado e análises de risco estão nos módulos de
`evaluation`.

## 6. Relatórios e notebooks

Os módulos de `reporting` transformam artefatos em tabelas e figuras. Os
notebooks não treinam novamente o modelo: carregam resultados versionados para
auditoria, exploração e visualização. Assim, a execução oficial permanece
reproduzível por comandos e não depende de estado oculto do kernel.

## Regras de leitura

- Não mover colunas entre splits sem atualizar o protocolo.
- Não usar `final_test` para seleção, calibração ou ajuste.
- Não alterar um artefato de `results/runs/`; criar um novo `run_id`.
- Ao adicionar uma variável, atualizar o dicionário de dados e os testes de
  vazamento antes de executar qualquer comparação.
