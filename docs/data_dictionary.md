# Dicionário de dados

**Estado:** esquema canônico `techqa_v1`, validado após a auditoria dos arquivos reais.

## Entidades principais

| Campo | Tipo canônico | Descrição | Disponível em produção? |
|---|---|---|---|
| `query_id` | string | Identificador estável da pergunta. | sim |
| `official_split` | string | Divisão original `train`, `dev` ou `validation`. | não como feature |
| `research_split` | string | `fit`, `calibration`, `selection`, `final_test` ou `smoke_test`. | não como feature |
| `question_group_id` | string | Hash que mantém perguntas idênticas no mesmo subconjunto interno. | não como feature |
| `question_title` | string | Título da pergunta técnica. | sim |
| `question_text` | string | Corpo da pergunta técnica. | sim |
| `query_text` | string | Título e corpo unidos para recuperação. | sim |
| `candidate_doc_ids` | lista de strings | Candidatos deduplicados preservando a ordem. | sim |
| `document_id` | string | Identificador do Technote. | sim |
| `title`, `text` | string | Título e corpo do Technote em `documents.parquet`. | sim |
| `answerable` | booleano | Conversão do rótulo nativo `ANSWERABLE`. | não como feature |
| `gold_document_id` | string anulável | Documento anotado para perguntas respondíveis. | não como feature |
| `answer_start`, `answer_end` | inteiro anulável | Intervalo gold `[início, fim)` no corpo. | não como feature |
| `scenario_id` | string | Identificador de variação experimental. | não como feature |
| `evidence_sufficient` | booleano | Rótulo derivado da presença da evidência. | alvo |

## Manifesto de contexto

Cada contexto derivado deverá registrar `query_id`, split, configuração de recuperação, valor de k, documentos e chunks incluídos, documentos removidos, razão do rótulo, seed, versão do código e hash dos dados. Os nomes brutos serão convertidos para `snake_case` em dados processados. Campos de construção não entram no conjunto de variáveis do modelo.

## Corpus de chunks

`chunks.parquet` registra `chunk_id`, `document_id`, `chunk_index`, `passage_text`,
`body_start_char`, `body_end_char`, `body_token_count` e `input_token_count`. Rankings não
contêm gold ou rótulos; esses campos aparecem somente em `evaluation.parquet`, impedindo que
a extração de features leia informação indisponível em produção.

## Variáveis previstas

Pontuações e estatísticas dos retrievers, margens, dispersão, sobreposição top-k, concordância de ranking, comprimento da pergunta e padrões textuais observáveis serão calculados somente a partir da consulta e da recuperação disponível em inferência.
