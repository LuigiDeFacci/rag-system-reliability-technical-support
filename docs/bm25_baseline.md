# Baseline BM25 documental

**Run:** `20260721-002321_bm25-doc_5c311f59`  
**Estado:** resultado interno preliminar; teste final não utilizado.

## Configuração

O índice calcula frequências documentais sobre os 28.461 Technotes candidatos únicos. Para cada pergunta, somente sua lista oficial de 49 ou 50 candidatos é ranqueada. O texto indexado é `title + text`.

O tokenizer aplica `casefold` e preserva identificadores técnicos com pontos, dois-pontos, barras e hífens, como `8.5.7.0` e `CVE-2016-6089`. Foram usados `k1=1,2` e `b=0,75`, sem ajuste de hiperparâmetros.

## Resultados internos

As métricas de retrieval consideram somente perguntas nativamente respondíveis.

| Split | MRR | Recall@1 | Recall@3 | Recall@5 | Recall@10 |
|---|---:|---:|---:|---:|---:|
| Fit | 0,521 | 0,444 | 0,556 | 0,589 | 0,667 |
| Calibração | 0,534 | 0,444 | 0,556 | 0,633 | 0,678 |
| Seleção | 0,553 | 0,500 | 0,589 | 0,611 | 0,656 |

No split de seleção, a taxa de contextos com evidência entre todas as perguntas foi 0,375 em top-1, 0,442 em top-3, 0,458 em top-5 e 0,492 em top-10. Esses valores não medem calibração nem qualidade de geração.

## Proteções e artefatos

O run contém configurações, hashes, rankings sem campos gold, avaliação separada e métricas agregadas. `final_test_used=false` foi verificado. O comando exige `--allow-test` e um arquivo de bloqueio integralmente congelado para acessar o desenvolvimento oficial.

