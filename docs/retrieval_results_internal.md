# Resultados internos de recuperação

**Estado:** preliminar; somente `fit`, `calibration` e `selection`. O teste final não foi
executado. Todos os métodos usam os mesmos 90.284 chunks e candidatos oficiais.

## Recall de contexto

O rótulo é positivo quando a união dos top-k chunks cobre continuamente o span anotado.
Valores abaixo consideram apenas perguntas nativamente respondíveis.

| Split | Método | @1 | @3 | @5 | @10 |
|---|---|---:|---:|---:|---:|
| fit | BM25 | 0,341 | 0,467 | 0,504 | 0,563 |
| fit | Semântico | 0,367 | 0,519 | 0,574 | 0,656 |
| fit | RRF | 0,370 | 0,474 | 0,563 | 0,611 |
| calibration | BM25 | 0,367 | 0,522 | 0,622 | 0,678 |
| calibration | Semântico | 0,433 | 0,567 | 0,622 | 0,733 |
| calibration | RRF | 0,411 | 0,544 | 0,600 | 0,689 |
| selection | BM25 | 0,411 | 0,467 | 0,478 | 0,578 |
| selection | Semântico | 0,333 | 0,522 | 0,600 | 0,644 |
| selection | RRF | 0,411 | 0,500 | 0,522 | 0,622 |

Na seleção, o RRF obteve o maior MRR para o primeiro chunk que contém sozinho o span
(0,475), contra 0,457 do BM25 e 0,447 do semântico. Contudo, não venceu uniformemente: o
semântico teve maior recall de contexto em @3, @5 e @10, enquanto BM25 e RRF empataram em
@1. Isso sustenta complementaridade entre sinais, não superioridade automática da fusão.

## Sensibilidade documental

Na seleção, Recall@10 da proxy documental foi 0,667 para BM25, 0,744 para semântico e
0,722 para RRF. Os valores são maiores que o recall de contexto, evidenciando que localizar o
documento correto não implica selecionar o trecho suficiente dentro do orçamento top-k.

## Runs auditados

- BM25: `20260721-015143_bm25-chunk_71a60532`
- Semântico: `20260721-015232_semantic-chunk_2a14e360`
- RRF: `20260721-015243_hybrid-rrf_d4583ffc`

Os três runs registram o commit `9d88d73`, não contêm gold nos arquivos de ranking e mantêm
avaliação separada. A escolha do k principal permanece aberta até a avaliação do classificador
de suficiência e das curvas risco-cobertura no split `selection`.
