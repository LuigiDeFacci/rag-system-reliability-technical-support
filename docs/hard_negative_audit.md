# Auditoria de negativos difíceis

**Versão:** `hard_negatives_v1`  
**Escopo:** somente `fit`, `calibration` e `selection`; teste final não utilizado.

## Construção

Para cada uma das 450 perguntas internas respondíveis, o documento gold foi removido por
inteiro dos rankings BM25 e semântico. Foram então selecionados os cinco chunks não-gold
mais bem ranqueados por BM25, pelo retriever semântico e por uma nova fusão RRF dos dois
rankings filtrados. Isso produziu 1.350 contextos: três por pergunta.

Cada linha registra `query_id`, split, método, chunks e documentos incluídos, documento
removido, scores, ranks, razão do rótulo, seed, commit e runs de origem. Verificações
automatizadas confirmam que cada contexto possui cinco chunks, que o gold não aparece nos
documentos incluídos e que todos os rótulos são zero. A definição operacional é ausência da
evidência anotada; outro Technote pode conter evidência equivalente não anotada.

## Conflitos técnicos

Produto, versão e código servem apenas para anotar cenários, nunca como features gold. A
regra forte exige: produto do gold presente entre os documentos recuperados, CVE explícito
na consulta, CVE explícito no contexto e conjuntos de CVE distintos. Ela identificou 87
contextos entre os três métodos, incluindo 31 híbridos. Na seleção, foram cinco híbridos.

Uma inspeção exploratória de 12 candidatos da regra geral mostrou ruído de timestamps,
IDs de páginas de suporte e números de fix pack. Por isso, 61 contextos híbridos ao longo dos
splits não foram promovidos a conflitos confirmados; continuam marcados como
`technical_conflict_candidate_hybrid` e requerem revisão. Essa separação evita transformar
uma heurística textual em verdade documental.

## Estresse do modelo congelado

O run `20260721-023427_hard-stress-k5_594f6518` aplicou o modelo interno já selecionado aos
90 contextos híbridos da seleção após remoção do gold. A prevalência é artificialmente zero,
portanto não se reportam ROC-AUC, PR-AUC nem calibração operacional.

| Política congelada | Falsa autorização | IC95% bootstrap |
|---|---:|---:|
| conservadora | 7,8% | 2,2%–13,3% |
| equilibrada | 25,6% | 16,7%–34,4% |
| expansiva | 31,1% | 22,2%–40,0% |

A probabilidade média caiu de 0,488 no contexto natural para 0,340 no contexto filtrado. A
mudança média pareada foi −0,149 (IC95% −0,199 a −0,101), mas a confiança diminuiu em
apenas 66,7% das perguntas. Os intervalos usam 2.000 reamostragens por `query_id`.

O resultado indica sensibilidade parcial à remoção da evidência e, ao mesmo tempo, uma taxa
material de falsa autorização em negativos difíceis. Ele é um teste de estresse interno, não
uma estimativa da prevalência ou do risco em produção.
