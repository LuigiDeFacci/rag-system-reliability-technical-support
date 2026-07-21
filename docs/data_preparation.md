# Preparação canônica dos dados

**Versão:** `techqa_v1`  
**Seed:** 42  
**Estado:** concluída e reproduzível.

## Entradas

A preparação lê exclusivamente os JSONs brutos auditados e o manifesto `data/manifests/techqa_audit.json`. Os dados brutos não são alterados.

## Transformações

1. Renomear campos para `snake_case` no parquet processado.
2. Converter `ANSWERABLE` para booleano e offsets para inteiros anuláveis.
3. Deduplicar candidatos preservando a primeira ocorrência. Isso altera somente `DEV_Q082` e `DEV_Q179`.
4. Criar `query_text` pela concatenação de título e corpo.
5. Marcar correspondência exata do span e sobreposição exata/próxima com o treino.
6. Excluir 21 Technotes que existem no arquivo documental, mas não são candidatos de nenhuma pergunta.

O corpus processado contém 28.461 documentos candidatos únicos.

## Divisão interna

As 600 perguntas oficiais de treino foram agrupadas pelo SHA-256 do título e corpo após `casefold` e normalização de espaços. Um algoritmo guloso determinístico distribuiu os grupos em cinco folds equilibrando tamanho e respondibilidade. O fold 0 é calibração, o fold 1 é seleção e os demais formam o ajuste.

| Split | Perguntas | Respondíveis | Não respondíveis | Grupos |
|---|---:|---:|---:|---:|
| Fit | 360 | 270 | 90 | 356 |
| Calibração | 120 | 90 | 30 | 119 |
| Seleção | 120 | 90 | 30 | 119 |
| Teste final local | 310 | 160 | 150 | 309 |
| Smoke test | 20 | 11 | 9 | 20 |

Nenhum grupo atravessa fit, calibração e seleção. O desenvolvimento oficial é apenas marcado como `final_test`; não foi usado na escolha do baseline.

## Artefatos

- `data/processed/techqa_v1/questions.parquet`
- `data/processed/techqa_v1/documents.parquet`
- `data/processed/techqa_v1/preparation_manifest.json`

Os hashes dos arquivos processados e de todas as entradas são registrados no manifesto. O script recusa sobrescrever um diretório existente.

