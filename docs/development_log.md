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

## 2026-07-20 — cenários, features e confiança

1. Foram materializados 2.400 contextos naturais, cobrindo as 600 perguntas internas e
   k em 1/3/5/10. O rótulo foi derivado do span no contexto, sem usar scores.
2. A extração produziu 45 features e separou fisicamente os rótulos. O `core_v1`, com 22
   features, foi congelado antes da avaliação dos modelos.
3. Regressões logísticas independentes por k foram ajustadas em `fit`; Platt e isotônica
   foram ajustados em `calibration`; todas as escolhas ocorreram em `selection`.
4. k=5 e a probabilidade bruta foram escolhidos internamente. Os três pontos operacionais
   foram derivados de risco ou F1 observados, e não de valores intuitivos.
5. Um bootstrap pareado agrupado por pergunta, com 2.000 réplicas, comparou o modelo aos
   sinais top-1. Cinco grupos de features foram avaliados por ablação.
6. Foram gerados quatro gráficos, tabelas de erros com hashes e o notebook
   `03_confidence_analysis.ipynb`. O notebook foi executado integralmente como verificação.
7. O teste final permaneceu bloqueado durante todas essas etapas.

## 2026-07-20 — negativos difíceis

1. O gold foi removido dos rankings de 450 perguntas respondíveis, após a separação dos
   splits. BM25, semântico e RRF produziram 1.350 contextos negativos auditáveis.
2. A primeira heurística de conflito técnico mostrou ruído em uma amostra exploratória. A
   classificação forte foi restringida a CVEs diferentes dentro do mesmo produto; os demais
   casos permanecem explicitamente como candidatos.
3. O artefato derivado foi regenerado após essa correção; o comando, os hashes e a razão da
   mudança ficaram registrados. Nenhum dado original foi removido.
4. O modelo e os limiares já selecionados foram aplicados aos 90 negativos híbridos de
   `selection`. A execução inicial sem IC foi preservada e substituída por um run com 2.000
   bootstraps agrupados por pergunta.
5. A falsa autorização no ponto equilibrado foi 25,6% (IC95% 16,7%–34,4%). O resultado foi
   documentado como estresse de prevalência zero, não como calibração ou risco operacional.

## 2026-07-20 — sensibilidade à prevalência

1. A seleção natural foi reponderada para prevalências positivas de 20%, 40%, 60% e 80%,
   mantendo scores, modelo, calibrador e limiares congelados.
2. Brier, ECE-10, cobertura e risco foram recalculados com pesos de classe. Foram usadas
   2.000 reamostragens por pergunta estratificadas pelo rótulo.
3. O risco equilibrado variou de 40,4% na prevalência de 20% para 4,1% na prevalência de
   80%, evidenciando que a política depende da mistura avaliada.
4. Nenhuma prevalência-alvo foi escolhida como operacional; a análise permanece uma
   sensibilidade interna e o teste final continua fechado.

## 2026-07-20 — congelamento do protocolo

1. Dados, recuperação, k=5, 22 features, regressão logística, probabilidade bruta, políticas,
   baselines, métricas, bootstrap, subconjuntos e saídas gráficas foram fixados em
   `configs/final_test_spec.yaml`.
2. Foi criado um avaliador final que exige flag explícita, worktree limpa, hash exato da
   especificação, ancestral Git congelado, hashes de dados/modelo e três runs gated.
3. O protocolo passou à versão 1.0. O gate permanece fechado até um commit separado registrar
   o hash e o commit congelado.

## 2026-07-20 — campanha final e relatório

1. O gate foi aberto uma vez no commit `6f4fe43`, vinculado à especificação `68bd89db...` e
   ao commit congelado `0d76d05`.
2. BM25, semântico e RRF avaliaram as mesmas 310 perguntas. Nenhuma decisão foi alterada
   entre as execuções.
3. O avaliador verificou hashes, ancestral Git e worktree limpa, aplicou o modelo congelado e
   executou 2.000 bootstraps pareados por pergunta.
4. O gate foi fechado no commit `975139b` antes da geração de relatórios.
5. As quatro figuras previstas, tabelas, lista de erros e manifesto foram gerados em
   `figures/final_test_v1/` pelo código versionado no commit `b84aecf`.
6. A hipótese foi classificada como parcialmente apoiada; resultados inferiores ou
   inconclusivos foram mantidos sem reabrir o protocolo.

## 2026-07-21 — risco em coberturas fixas e revisão da contribuição

1. As previsões finais congeladas foram comparadas em coberturas de 10%, 20%, 40%, 60%,
   80% e 100%, sem refit, recalibração, seleção de limiar ou reabertura do gate.
2. O run `20260721-122015_fixed-coverage_430de878` aplicou 2.000 bootstraps pareados por
   pergunta e inclusão fracionária na fronteira para tornar empates do RRF auditáveis.
3. A logística apresentou menor risco observado que o RRF até 40%, mas os IC95% das
   diferenças incluíram zero; em 60% e 80%, o RRF foi ligeiramente melhor.
4. A redação passou a distinguir o desenvolvimento oficial usado como holdout final local
   do conjunto cego original de 490 perguntas e a limitar “não respondível” ao universo dos
   candidatos oficiais.
5. A contribuição foi reenquadrada como evidência da distância entre discriminação,
   definição de limiar e controle de risco sob mudança de distribuição.
6. Os relatórios visuais foram regenerados em `figures/final_test_v2/` com “holdout final
   local” nos títulos e a classe negativa descrita como ausência de evidência nos candidatos.
   A versão v1 foi preservada para rastreabilidade.
7. A tabela, as comparações pareadas e a figura de coberturas fixas foram materializadas em
   `figures/fixed_coverage_v1/`; o notebook `07_fixed_coverage_risk.ipynb` foi executado.

## 2026-07-21 — consolidação científica e documental

1. Nenhum experimento foi executado e nenhuma configuração congelada foi alterada. A
   consolidação leu somente métricas, previsões e relatórios já existentes.
2. As perguntas do manuscrito foram ligadas às evidências em
   `research_questions_evidence_matrix.md`, separando resultados descritivos, diferenças
   estatisticamente sustentadas e interpretação gerencial.
3. `final_results.md` e `tcc_results_draft.md` foram reorganizados para responder
   diretamente às perguntas, apresentar coberturas fixas como evidência principal e tratar a
   falha de transferência do limiar como achado.
4. As fontes primárias de Joren et al. (2025), Chen et al. (2024), Kamath, Jia e Liang
   (2020), Qiu, Han e Huang (2026) e Geissler et al. (2026) foram verificadas antes do
   diálogo com a literatura.
5. `chapters_8_10_replacement_checklist.md` registrou os elementos que deverão substituir o
   conteúdo prospectivo do DOCX. O manuscrito não foi modificado.
