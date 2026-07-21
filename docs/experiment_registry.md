# Registro de experimentos

A primeira execução interna foi realizada. Nenhum teste final foi aberto.

## Execuções

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
