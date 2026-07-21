# Resultados finais

**Run:** `20260721-024728_final-test-k5_68bd89db`  
**Especificação:** SHA-256 `68bd89db...`; commit congelado `0d76d05`.  
**Procedimento:** 310 perguntas do desenvolvimento oficial, usado como holdout final local;
sem refit, recalibração ou alteração de limiar; gate fechado após a execução. Esse conjunto
não é o teste cego original de 490 perguntas do TechQA.

## Recuperação

| Método | MRR de chunk | Context R@1 | R@3 | R@5 | R@10 |
|---|---:|---:|---:|---:|---:|
| BM25 | 0,470 | 0,344 | 0,581 | 0,625 | 0,656 |
| Semântico | 0,496 | 0,369 | 0,563 | 0,631 | 0,744 |
| RRF | 0,531 | 0,419 | 0,606 | 0,656 | 0,744 |

O RRF apresentou o maior MRR e o maior recall contextual até k=5; em k=10 empatou com o
semântico. Em k=5, 105 das 160 perguntas respondíveis tiveram o span coberto, gerando
prevalência final de suficiência de 33,9% entre todas as 310 perguntas.

## Confiança e calibração

| Subconjunto | n | ROC-AUC | PR-AUC | Brier | ECE-10 | AURC |
|---|---:|---:|---:|---:|---:|---:|
| desenvolvimento oficial | 310 | 0,744 | 0,604 | 0,195 | 0,082 | 0,478 |
| sem duplicatas exatas | 288 | 0,742 | 0,583 | 0,194 | 0,092 | 0,505 |
| sem flags de quase duplicata | 267 | 0,738 | 0,574 | 0,195 | 0,099 | 0,513 |

As sensibilidades mantiveram ROC-AUC semelhante, indicando que duplicatas conhecidas não
explicam o resultado. Em relação à seleção interna, houve queda de ROC-AUC (0,864→0,744),
PR-AUC (0,793→0,604) e aumento de Brier (0,148→0,195) e AURC (0,348→0,478). O ECE menor
não compensa essa perda: o diagrama mostra sobreconfiança nas faixas altas.

## Políticas congeladas

| Política | Cobertura | Risco | Precisão | Recall | F1 |
|---|---:|---:|---:|---:|---:|
| conservadora | 13,5% | 35,7% | 0,643 | 0,257 | 0,367 |
| equilibrada | 41,6% | 45,7% | 0,543 | 0,667 | 0,598 |
| expansiva | 42,9% | 46,6% | 0,534 | 0,676 | 0,597 |

Os nomes descrevem o critério usado na seleção, não garantias fora dela. O limite
conservador, escolhido para risco interno ≤10%, atingiu 35,7% no holdout. Para risco final
observado ≤10%, a cobertura possível foi apenas 2,3%. Logo, os pontos gerenciais não são
transferíveis sem validação na distribuição de destino.

## Comparação com sinais isolados

| Método | ROC-AUC | PR-AUC | AURC |
|---|---:|---:|---:|
| logística | 0,744 | 0,604 | 0,478 |
| BM25 top-1 | 0,503 | 0,346 | 0,663 |
| semântico top-1 | 0,628 | 0,450 | 0,574 |
| RRF top-1 | 0,720 | 0,504 | 0,546 |

Contra RRF, a melhoria foi 0,024 em ROC-AUC (IC95% −0,023–0,067), 0,100 em PR-AUC
(0,034–0,172) e 0,068 de redução da AURC (−0,005–0,096). Assim, houve ganho confirmado em
PR-AUC, mas os intervalos de ROC-AUC e AURC incluem zero. Contra BM25 e semântico, os três
intervalos ficaram acima de zero.

## Risco em coberturas comparáveis

| Cobertura | Logística | BM25 top-1 | Semântico top-1 | RRF top-1 |
|---:|---:|---:|---:|---:|
| 10% | 32,3% | 64,5% | 51,6% | 45,3% |
| 20% | 35,5% | 66,1% | 50,0% | 45,3% |
| 40% | 45,2% | 66,1% | 56,5% | 47,9% |
| 60% | 53,8% | 64,0% | 60,8% | 53,3% |
| 80% | 60,1% | 65,7% | 62,5% | 59,7% |
| 100% | 66,1% | 66,1% | 66,1% | 66,1% |

A análise pós-hoc `20260721-122015_fixed-coverage_430de878` usou somente as previsões
congeladas. A logística teve menor risco observado que o RRF em 10%, 20% e 40%, mas os
IC95% pareados das reduções incluíram zero. Em 60% e 80%, o RRF foi ligeiramente melhor.
Empates na fronteira foram tratados por inclusão fracionária, evitando dependência da ordem
arbitrária das linhas.

## Erros e conclusão

Na política equilibrada, a matriz foi `[[146,59],[35,70]]`: 59 falsas autorizações e 35
abstenções indevidas. Das falsas autorizações, 47 eram perguntas sem resposta anotada entre
os 50 Technotes candidatos oficiais e 12 eram misses de recuperação. Essa classe não
significa que a pergunta seja universalmente impossível de responder. O mecanismo distingue
grupos em média, mas ainda atribui confiança alta a contextos tecnicamente plausíveis sem
evidência anotada.

A hipótese recebe apoio parcial. A combinação superou os baselines baseados em sinais
isolados de BM25 e recuperação semântica. Porém, não demonstrou vantagem uniforme sobre o
RRF nas métricas globais ou em coberturas fixas, e os riscos dos limiares gerenciais não se
generalizaram. A contribuição empírica central é mostrar a distância entre ordenar casos por
confiança, escolher um limiar e controlar risco em outra distribuição. O mecanismo é útil
como sinal de ordenação, mas a versão avaliada não deve ser tratada como política de
autorização pronta para produção.
