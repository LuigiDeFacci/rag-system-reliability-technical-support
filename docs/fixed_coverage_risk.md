# Risco em coberturas fixas

**Run:** `20260721-122015_fixed-coverage_430de878`  
**Fonte:** previsões congeladas de `20260721-024728_final-test-k5_68bd89db`  
**Escopo:** análise pós-hoc; nenhum refit, recalibração, escolha de limiar ou reabertura do gate.

## Resultado principal

Define-se Δrisco como `risco(logística) − risco(RRF)`; valores negativos favorecem a
logística.

| Cobertura | Casos respondidos (aprox.) | Logística | BM25 top-1 | Semântico top-1 | RRF top-1 | Δrisco vs. RRF | IC95% do Δ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10% | 31 | 32,3% | 64,5% | 51,6% | 45,3% | −13,0 p.p. | [−28,7; 3,2] |
| 20% | 62 | 35,5% | 66,1% | 50,0% | 45,3% | −9,8 p.p. | [−18,5; 2,7] |
| 40% | 124 | 45,2% | 66,1% | 56,5% | 47,9% | −2,7 p.p. | [−8,9; 2,3] |
| 60% | 186 | 53,8% | 64,0% | 60,8% | 53,3% | +0,4 p.p. | [−2,9; 4,3] |
| 80% | 248 | 60,1% | 65,7% | 62,5% | 59,7% | +0,3 p.p. | [−2,0; 2,3] |
| 100% | 310 | 66,1% | 66,1% | 66,1% | 66,1% | 0,0 p.p. | [0,0; 0,0] |

Risco é a proporção esperada de contextos insuficientes entre os casos autorizados. Em
10%, 20% e 40% de cobertura, a logística reduziu descritivamente o risco frente ao RRF em
13,0, 9,8 e 2,7 pontos percentuais. Todos os IC95% pareados incluem zero. Em 60% e 80%, o
RRF teve risco descritivo 0,4 e 0,3 ponto menor. Em 100%, os métodos aceitam o mesmo
conjunto.

## Método

As 310 perguntas do desenvolvimento oficial, usado como holdout final local, foram
reamostradas de forma pareada 2.000 vezes por `query_id`, com seed 42. Como o RRF produz
muitos empates, a fronteira usa inclusão fracionária: o risco esperado seleciona uma fração
aleatória do grupo empatado, em vez de depender da ordem arbitrária das linhas. Esse detalhe
explica o mesmo risco do RRF em 10% e 20%.

## Resposta à hipótese

A regressão apresenta risco descritivo menor que BM25 em todas as coberturas parciais e que
o semântico sobretudo nas coberturas intermediárias. Contra o RRF, porém, a vantagem não é
uniforme nem estatisticamente sustentada. Assim, a hipótese de menor risco em coberturas
comparáveis recebe **apoio parcial**. O achado mais robusto é que melhor discriminação não
produziu uma política estática de autorização com risco transferível ao holdout.
