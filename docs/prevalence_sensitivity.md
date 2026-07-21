# Sensibilidade à prevalência

**Run:** `20260721-023732_prevalence-k5_a3a584f3`  
**Escopo:** seleção interna; k=5; probabilidade bruta; teste final não utilizado.

A distribuição condicional dos scores foi mantida fixa e as classes foram ponderadas para
prevalências positivas de 20%, 40%, 60% e 80%. O modelo não foi reajustado nem recalibrado.
Essa análise responde “o que ocorreria sob outra mistura das mesmas classes?”, não estima a
prevalência operacional.

| Prevalência-alvo | Prob. média | Brier | ECE-10 | Risco equilibrado | Cobertura equilibrada |
|---:|---:|---:|---:|---:|---:|
| 20% | 0,366 | 0,136 | 0,194 | 40,4% | 27,1% |
| 40% | 0,433 | 0,148 | 0,097 | 20,3% | 40,6% |
| 60% | 0,500 | 0,161 | 0,132 | 10,1% | 54,0% |
| 80% | 0,566 | 0,174 | 0,237 | 4,1% | 67,4% |

O ECE foi menor perto da prevalência observada de 39,2% e aumentou nos extremos. Na mistura
com apenas 20% de positivos, o mesmo limiar equilibrado teria risco seletivo estimado de
40,4% (IC95% 23,9%–52,5%), quase o dobro do risco observado na distribuição original. Isso
demonstra que uma probabilidade ou política não deve ser transferida para outra prevalência
sem validação local.

Os intervalos usam 2.000 reamostragens por `query_id`, estratificadas pelo rótulo para manter
a interpretação da prevalência-alvo. Como a análise apenas repondera os mesmos casos, ela
não representa mudança de domínio, drift temporal nem surgimento de novos tipos de erro.
