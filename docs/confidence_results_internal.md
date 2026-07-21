# Resultados internos do mecanismo de confiança

**Escopo:** seleção interna do treino oficial; `k=5`; teste final não executado.  
**Run selecionado:** `20260721-021033_confidence-logreg_27fc4ef8`.  
**Robustez:** `20260721-021427_robustness-k5_1dacdb1b`.

## Configuração avaliada

Uma regressão logística foi ajustada em `fit` com 22 features previamente fixadas. O
`StandardScaler` foi ajustado no mesmo split. Platt e isotônica foram ajustados somente em
`calibration`; `selection` foi usado para escolher k, calibrador e políticas. Cada pergunta
contribui com um contexto natural por k. Em `selection`, k=5 possui 120 perguntas e
prevalência de suficiência de 39,2% (47/120).

## Discriminação, calibração e decisão seletiva

| Método em k=5 | ROC-AUC | PR-AUC | Brier | ECE-10 | AURC |
|---|---:|---:|---:|---:|---:|
| Logística bruta | 0,864 | 0,793 | 0,148 | 0,098 | 0,348 |
| Platt | 0,864 | 0,793 | 0,162 | 0,148 | 0,348 |
| Isotônica | 0,855 | 0,756 | 0,154 | 0,137 | 0,358 |

A probabilidade bruta foi mantida pelo menor Brier em seleção. Isso não demonstra
calibração universal: a estimativa vale para a prevalência e a construção avaliadas. O ECE
usa dez intervalos de largura igual. A AURC é a média discreta do risco acumulado após
ordenar os 120 casos por confiança decrescente.

| Política | Limiar | Cobertura | Risco observado |
|---|---:|---:|---:|
| Conservadora: risco ≤10% | 0,731 | 18,3% | 9,1% |
| Equilibrada: F1 máximo | 0,429 | 40,0% | 20,8% |
| Expansiva: risco ≤30% | 0,414 | 45,8% | 29,1% |

No ponto equilibrado, precisão=0,792, recall=0,809 e F1=0,800, com 10 falsos positivos e
9 falsos negativos. Esses pontos são proxies experimentais, não estimativas de produtividade.

## Comparação e robustez

| Sinal isolado | ROC-AUC | PR-AUC | AURC | Melhor F1 |
|---|---:|---:|---:|---:|
| BM25 top-1 | 0,604 | 0,477 | 0,546 | 0,587 |
| Semântico top-1 | 0,714 | 0,612 | 0,451 | 0,647 |
| RRF top-1 | 0,766 | 0,594 | 0,448 | 0,705 |

No bootstrap pareado por `query_id`, com 2.000 réplicas, a melhoria da logística sobre o
RRF top-1 foi 0,098 em ROC-AUC (IC95% 0,022–0,170), 0,199 em PR-AUC
(0,091–0,332) e 0,100 de redução da AURC (0,014–0,189). Os intervalos são internos e não
substituem o holdout.

Na ablação, o conjunto completo obteve o maior ROC-AUC (0,864) e F1 (0,800). O grupo
semântico isolado ficou marginalmente melhor em PR-AUC (0,793 contra 0,793 após
arredondamento; diferença 0,0008) e AURC (0,346 contra 0,348). Portanto, a ablação não
sustenta que toda feature acrescenta valor a toda métrica.

## Análise de erros

Dos dez falsos positivos do ponto equilibrado, oito eram `natural_retrieval_miss` e dois
perguntas nativamente não respondíveis. A inspeção mostra candidatos muito semelhantes à
pergunta — por vezes com o mesmo erro ou produto no título — mas sem o span anotado no
contexto. Os nove falsos negativos eram contextos suficientes; apareceram em consultas com
versões, boletins e documentos quase duplicados, nas quais a evidência estava presente mas
os sinais agregados ficaram fracos. Essa análise motiva um conjunto separado de negativos
difíceis e uma auditoria de conflitos técnicos antes do congelamento.

As figuras e as listas de erros reproduzíveis estão em `figures/internal_selection_v1/` e o
notebook de leitura está em `notebooks/03_confidence_analysis.ipynb`.
