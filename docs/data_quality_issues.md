# Questões de qualidade dos dados

Este registro separa defeitos do release de decisões de processamento. Os arquivos brutos nunca serão corrigidos in place.

## QD-001 — Divergência entre span e `ANSWER`

**Afetados:** `DEV_Q014`, `DEV_Q029`, `DEV_Q038`, `DEV_Q094`, `DEV_Q129`, `DEV_Q156`, `DEV_Q160`, `DEV_Q180`, `DEV_Q291`, `DEV_Q300` e `DEV_Q303`. `VAL_Q014` replica `DEV_Q014`.

**Revisão:** oito divergências são explicadas por URLs, capitalização, marcadores ou espaços; duas possuem `ANSWER` vazio, mas a região indicada contém resposta direta; `DEV_Q291` aponta para uma região mais ampla que sustenta a resposta por tabela e explicação. Todos os offsets estão dentro do documento correto.

**Tratamento:** preservar o registro bruto, usar os offsets como região gold para suficiência e marcar `span_exact_match=false`. Reportar análise de sensibilidade em nível documental.

## QD-002 — Candidatos duplicados ou ausentes

- `DEV_Q082` e `DEV_Q179` repetem o documento gold dentro dos 50 IDs.
- `DEV_Q177` contém apenas 49 IDs.

**Tratamento:** deduplicar IDs preservando a primeira ocorrência. Não preencher artificialmente o candidato ausente.

## QD-003 — Perguntas duplicadas

Há seis grupos exatos dentro do treino, um dentro do desenvolvimento e 22 textos exatos entre treino e desenvolvimento. Sete pares entre splits têm respondibilidade diferente porque a composição dos candidatos difere. Uma triagem TF-IDF identificou outros 27 pares não exatos com similaridade mínima de 0,90; os títulos e corpos correspondem a variações claras do mesmo chamado, mas o agrupamento final será versionado.

**Tratamento:** agrupar duplicatas dentro das subdivisões de treino. Reportar o desenvolvimento oficial completo, uma versão sem duplicatas exatas de treino e uma análise secundária agrupada incluindo as quase duplicatas aprovadas.

## QD-004 — Validação técnica não independente

As 20 perguntas de `validation/` reproduzem as primeiras 20 de desenvolvimento e todos os seus 994 documentos aparecem no conjunto documental de desenvolvimento.

**Tratamento:** usar somente para validar formato e execução, nunca para calibrar, escolher modelos ou estimar desempenho.

## QD-005 — Documentos duplicados

O conjunto de Technotes de treino/desenvolvimento possui quatro grupos de textos idênticos, abrangendo nove IDs.

**Tratamento:** manter IDs para rastreabilidade, mas auditar se documentos textualmente idênticos devem compartilhar grupo em análises de vazamento.

