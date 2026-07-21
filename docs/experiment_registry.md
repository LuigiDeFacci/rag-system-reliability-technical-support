# Registro de experimentos

A primeira execução interna foi realizada. Nenhum teste final foi aberto.

## Execuções

### Retrieval por chunks — commit `9d88d73`

| Run | Método | Estado | Resultado em `selection` |
|---|---|---|---|
| `20260721-015143_bm25-chunk_71a60532` | BM25, `k1=1,2`, `b=0,75` | validado | contexto R@1 0,411; R@10 0,578; MRR de chunk 0,457 |
| `20260721-015232_semantic-chunk_2a14e360` | BGE v1.5 fixado | validado | contexto R@1 0,333; R@10 0,644; MRR de chunk 0,447 |
| `20260721-015243_hybrid-rrf_d4583ffc` | RRF, constante 60 | validado | contexto R@1 0,411; R@10 0,622; MRR de chunk 0,475 |

Cada run contém 600 perguntas internas, hashes válidos, scores finitos e rankings sem campos
gold. `final_test_used=false` nos três manifestos.

### Cenários e confiança — commits `89cc536` a `0460389`

| Run/artefato | Estado | Finalidade e resultado |
|---|---|---|
| `natural_scenarios_v1` | validado | 2.400 contextos naturais; 600 perguntas × k em 1/3/5/10; teste não usado |
| `features_natural_v1` | validado | 45 features disponíveis em produção; rótulos e metadados de avaliação separados |
| `20260721-020539_confidence-logreg_715c4e06` | substituído | primeira execução; comparação seletiva contra baselines ainda incompleta |
| `20260721-020801_confidence-logreg_715c4e06` | substituído | comparação completa; critério expansivo não garantia cobertura maior que o equilibrado |
| `20260721-021033_confidence-logreg_27fc4ef8` | selecionado internamente | k=5, logística bruta: ROC-AUC 0,864; PR-AUC 0,793; Brier 0,148; AURC 0,348 |
| `20260721-021427_robustness-k5_1dacdb1b` | validado | bootstrap agrupado pareado com 2.000 réplicas e cinco ablações |
| `hard_negatives_v1` | validado | 1.350 contextos não-gold em BM25, semântico e RRF; 38 perguntas e 87 contextos com conflito exato de CVE |
| `20260721-023120_hard-stress-k5_4e69b1bc` | substituído | primeira avaliação de estresse; ainda sem intervalos de confiança |
| `20260721-023156_hard-stress-k5_594f6518` | substituído | métricas completas, mas executado antes do commit que formalizou a implementação |
| `20260721-023427_hard-stress-k5_594f6518` | validado | commit `6d4a298`; falsa autorização equilibrada 25,6% (IC95% 16,7%–34,4%) em 90 negativos híbridos |
| `20260721-023732_prevalence-k5_a3a584f3` | validado | reponderação interna em prevalências 20/40/60/80%; nenhum refit ou recalibração |

### Campanha final congelada — especificação `68bd89db`

| Run | Método | Resultado principal |
|---|---|---|
| `20260721-024512_bm25-chunk_7ee3b20f` | BM25 final | contexto R@5 0,625; MRR 0,470 |
| `20260721-024558_semantic-chunk_94a0111c` | BGE final | contexto R@5 0,631; MRR 0,496 |
| `20260721-024610_hybrid-rrf_24707106` | RRF final | contexto R@5 0,656; MRR 0,531 |
| `20260721-024728_final-test-k5_68bd89db` | confiança final | ROC-AUC 0,744; PR-AUC 0,604; Brier 0,195; AURC 0,478 |

Os quatro runs declaram `final_test_used=true`. O avaliador declara
`no_refit_or_recalibration=true`; o gate foi fechado após a campanha.

Os dois runs substituídos não foram apagados localmente. O run selecionado contém modelos,
predições, coeficientes, bins de confiabilidade, configuração e hashes. Todos declaram
`final_test_used=false`.

### `embedding_benchmark_cpu`

| Campo | Valor |
|---|---|
| objetivo | Medir viabilidade da codificação BGE em CPU |
| estado | benchmark técnico; não é resultado experimental |
| dados | primeiros 256 chunks de `chunks_bge_v1` |
| modelo | `BAAI/bge-small-en-v1.5`, revisão `5c38ec7...` |
| ambiente | Python 3.10.2; PyTorch 2.13.0 CPU; Sentence Transformers 5.6.0 |
| resultado | 53,72 s; 4,77 chunks/s; dimensão 384 |
| teste final | não utilizado |
| artefatos | `data/interim/embedding_benchmark_cpu/` |

Esse benchmark existe somente para escolher o dispositivo de execução; não participa da
seleção de modelo, features, k ou thresholds.

### `embedding_benchmark_cuda_b32`

| Campo | Valor |
|---|---|
| objetivo | Validar compatibilidade e throughput da GTX 1650 |
| estado | benchmark técnico; não é resultado experimental |
| dados | primeiros 256 chunks de `chunks_bge_v1` |
| ambiente | Python 3.10.2; PyTorch 2.11.0+cu128; batch 32 |
| resultado | 5,88 s; 43,57 chunks/s; 9,14 vezes o throughput CPU |
| teste final | não utilizado |
| artefatos | `data/interim/embedding_benchmark_cuda_b32/` |

### `20260721-002321_bm25-doc_5c311f59`

| Campo | Valor |
|---|---|
| objetivo | Baseline BM25 documental fixo |
| estado | executado e validado internamente |
| configuração | SHA-256 `5c311f59cc4751a1146f7eefec08db2fab6ed7690976c135cc28538d717bb22f` |
| commit | não disponível; repositório ainda sem commit inicial |
| dados | `techqa_v1` |
| splits usados | fit, calibração e seleção |
| teste final | não utilizado |
| artefatos | `results/runs/20260721-002321_bm25-doc_5c311f59/` |
| resultado de seleção | MRR 0,553; Recall@1 0,500; Recall@10 0,656 |

## Modelo para novas entradas

| Campo | Valor |
|---|---|
| `run_id` | `YYYYMMDD-HHMMSS_<nome-curto>` |
| objetivo | |
| estado | planejado / executado / inválido |
| configuração | caminho + SHA-256 |
| commit | hash Git |
| dados | versão + hashes |
| seed | |
| ambiente | Python, SO e lockfile |
| modelo de embeddings | nome + revisão |
| splits usados | |
| métricas principais | |
| artefatos | `results/runs/<run_id>/` |
| observações | |

Runs nunca serão sobrescritos. Uma execução inválida permanece registrada com a justificativa.
