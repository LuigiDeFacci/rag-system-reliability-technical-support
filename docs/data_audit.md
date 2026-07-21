# Auditoria do TechQA

**Estado:** auditoria inicial dos arquivos reais concluída; revisão manual de casos excepcionais pendente.  
**Data:** 20 de julho de 2026.

## Aquisição e integridade

O arquivo `TechQA.tar.gz` foi obtido da distribuição pública `PrimeQA/TechQA`, indicada pelo repositório oficial `IBM/techqa`.

- Tamanho: 2.959.973.525 bytes.
- SHA-256: `6b094ef9a69718f727ce8d7e15c4d961e51032cefaa952e0d6af9d176d7ba118`.
- Conteúdo: 21 entradas, sem caminhos absolutos ou componentes `..`.
- Tamanho descompactado integral: 12.871.140.164 bytes.

Foram extraídas somente as anotações, os documentos candidatos e os arquivos de validação. As representações redundantes do corpus completo permanecem no tar para preservar espaço.

## Licença

O `README.txt` e o PDF incluídos no arquivo estabelecem **Community Data License Agreement — Permissive — Version 1.0 (CDLA-Permissive-1.0)** para o dataset e, separadamente, para o corpus de Technotes. Isso prevalece sobre a etiqueta Apache-2.0 exibida na página de hospedagem. Código próprio e dados devem ter licenças e atribuições separadas.

## Esquema confirmado

As perguntas usam `QUESTION_ID`, `QUESTION_TITLE`, `QUESTION_TEXT`, `DOC_IDS`, `ANSWERABLE`, `DOCUMENT`, `START_OFFSET`, `END_OFFSET` e `ANSWER`. O nome real é `QUESTION_TEXT`, não `QUESTION_BODY`. Os documentos possuem `id`, `title`, `text`, `content` e `metadata`; todos os registros inspecionados têm produto, ID de produto, data, URL canônica e ID de origem preenchidos.

| Conjunto | Perguntas | Respondíveis | Não respondíveis | Documentos candidatos únicos |
|---|---:|---:|---:|---:|
| Treino | 600 | 450 | 150 | 20.777 |
| Desenvolvimento | 310 | 160 | 150 | 12.355 |
| Validação técnica | 20 | 11 | 9 | 994 |

Cada pergunta de treino possui 50 candidatos. Em desenvolvimento, `DEV_Q177` possui 49. `DEV_Q082` e `DEV_Q179` possuem um documento gold duplicado na lista; a preparação deduplicará IDs preservando a ordem.

A publicação original descreve ainda um conjunto cego de avaliação com 490 perguntas, cujos
rótulos não integram o release usado nesta pesquisa. Por isso, as 310 perguntas acima são o
**desenvolvimento oficial usado como holdout final local**, não o “teste oficial”. No TechQA,
uma pergunta é rotulada não respondível quando os anotadores não encontram resposta entre
os 50 Technotes candidatos fornecidos; isso não equivale a impossibilidade universal de
resposta. Fonte: [TechQA: A Dataset for New Models of Technical Question Answering](https://aclanthology.org/2020.acl-main.117/).

## Documentos e spans

O arquivo de treino/desenvolvimento contém 28.482 Technotes; o de validação contém 995. Não há textos vazios ou divergências entre a chave do mapa e o campo `id`. Há quatro grupos de texto documental duplicado, totalizando nove IDs.

Todos os 450 spans de treino reproduzem exatamente `text[start:end]`. Em desenvolvimento, 11 dos 160 casos respondíveis divergem do campo `ANSWER`; dois possuem `ANSWER` vazio, dois diferem apenas em espaços e outros incluem diferenças de links, capitalização ou amplitude. Os offsets são válidos e os documentos gold existem. Esses casos serão revisados individualmente antes de congelar o rótulo de trecho.

## Sobreposição e vazamento

- Existem seis grupos de perguntas exatamente duplicadas dentro do treino; dois têm respondibilidade diferente por usarem candidatos distintos.
- Existe um grupo duplicado dentro do desenvolvimento.
- Há 22 textos de pergunta exatamente iguais entre treino e desenvolvimento; sete pares têm respondibilidade diferente.
- Uma triagem TF-IDF com limiar 0,90 encontrou 49 pares próximos entre treino e desenvolvimento, envolvendo 46 perguntas de treino e 43 de desenvolvimento. Isso é apenas uma lista de revisão, não um critério definitivo de exclusão.
- As 20 perguntas de `validation/` são cópias exatas das primeiras 20 perguntas de desenvolvimento. Esse diretório serve somente como smoke test do formato oficial.
- Treino e desenvolvimento compartilham 4.671 documentos candidatos.

## Implicações para o protocolo

O experimento principal reranqueará os candidatos oficiais. O rótulo de não respondibilidade só foi validado nesse universo; recuperar livremente nos 801.998 Technotes poderia encontrar evidência não anotada e criar falsos negativos.

O desenvolvimento oficial será mantido como holdout final para comparabilidade. Também serão reportados resultados sem duplicatas exatas de treino e uma análise secundária com agrupamento por pergunta. Nenhuma dessas transformações será apresentada como split oficial.

O manifesto completo é regenerado por `src/rag_confidence/data/audit.py` em `data/manifests/techqa_audit.json`.
