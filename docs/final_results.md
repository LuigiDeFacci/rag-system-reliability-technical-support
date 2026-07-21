# Resultados finais

**Run principal:** `20260721-024728_final-test-k5_68bd89db`

**Análise pós-hoc:** `20260721-122015_fixed-coverage_430de878`

**Especificação congelada:** SHA-256 `68bd89db...`; commit `0d76d05`

**Escopo:** 310 perguntas do desenvolvimento oficial do TechQA, usado como holdout final
local, e não o teste cego oficial de 490 perguntas. Não houve refit, recalibração ou mudança
de features, modelos, limiares, coberturas ou métodos estatísticos.

## Respostas às perguntas do TCC

### A combinação permite estimar suficiência documental?

**Parcialmente.** A regressão logística obteve ROC-AUC 0,744, PR-AUC 0,604, Brier 0,195,
ECE-10 0,082 e AURC 0,478. Esses valores indicam ordenação útil, mas não autorização segura:
houve sobreconfiança nas faixas altas e os riscos dos limiares definidos internamente não se
transferiram ao holdout.

### O risco é menor em coberturas comparáveis?

**Parcialmente.** A tabela de coberturas fixas é a evidência principal. Define-se Δrisco
como `risco(logística) − risco(RRF)`; valores negativos favorecem a logística.

| Cobertura | Casos | Logística | BM25 | Semântico | RRF | Δrisco vs. RRF | IC95% do Δ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10% | 31 | 32,3% | 64,5% | 51,6% | 45,3% | −13,0 p.p. | [−28,7; 3,2] |
| 20% | 62 | 35,5% | 66,1% | 50,0% | 45,3% | −9,8 p.p. | [−18,5; 2,7] |
| 40% | 124 | 45,2% | 66,1% | 56,5% | 47,9% | −2,7 p.p. | [−8,9; 2,3] |
| 60% | 186 | 53,8% | 64,0% | 60,8% | 53,3% | +0,4 p.p. | [−2,9; 4,3] |
| 80% | 248 | 60,1% | 65,7% | 62,5% | 59,7% | +0,3 p.p. | [−2,0; 2,3] |
| 100% | 310 | 66,1% | 66,1% | 66,1% | 66,1% | 0,0 p.p. | [0,0; 0,0] |

| Cobertura | Logística−BM25 (IC95%) | Logística−semântico (IC95%) | Logística−RRF (IC95%) |
|---:|---:|---:|---:|
| 10% | −32,3 [−58,1; −12,9] p.p. | −19,4 [−38,7; 3,2] p.p. | −13,0 [−28,7; 3,2] p.p. |
| 20% | −30,6 [−43,5; −16,1] p.p. | −14,5 [−25,8; 0,0] p.p. | −9,8 [−18,5; 2,7] p.p. |
| 40% | −21,0 [−30,6; −13,7] p.p. | −11,3 [−19,4; −4,0] p.p. | −2,7 [−8,9; 2,3] p.p. |
| 60% | −10,2 [−16,1; −5,4] p.p. | −7,0 [−11,3; −1,6] p.p. | +0,4 [−2,9; 4,3] p.p. |
| 80% | −5,6 [−8,9; −2,8] p.p. | −2,4 [−5,6; 0,4] p.p. | +0,3 [−2,0; 2,3] p.p. |
| 100% | 0,0 [0,0; 0,0] p.p. | 0,0 [0,0; 0,0] p.p. | 0,0 [0,0; 0,0] p.p. |

A logística teve menor risco estatisticamente sustentado contra BM25 em 10%–80% e contra o
semântico em 40% e 60%. Contra o semântico em 10%, 20% e 80%, a diferença foi apenas
descritiva. Contra RRF, houve menor risco descritivo até 40%, mas nenhum IC95% parcial
excluiu zero; em 60% e 80%, o RRF foi ligeiramente melhor. Empates na fronteira foram
tratados por inclusão fracionária. O bootstrap foi pareado por `query_id`, com 2.000
reamostragens e seed 42.

### Como a tolerância ao risco afeta cobertura e encaminhamento?

**A relação foi descrita, mas os nomes das políticas não constituem garantias.**

| Política congelada | Respostas | Encaminhamentos | Cobertura | Risco |
|---|---:|---:|---:|---:|
| conservadora | 42 | 268 | 13,5% | 35,7% |
| equilibrada | 129 | 181 | 41,6% | 45,7% |
| expansiva | 133 | 177 | 42,9% | 46,6% |

O limiar conservador havia sido escolhido para risco interno ≤10%, mas atingiu 35,7% no
holdout. Retrospectivamente, risco observado ≤10% ocorreu nos primeiros 2,3% do holdout,
aproximadamente sete respostas. Essa cobertura é um diagnóstico retrospectivo do holdout;
não representa um novo limiar selecionado nem uma política validada. O achado é que o
limiar interno não preservou seu nível de risco; a
causa não foi identificada, embora a política possa ser sensível à distribuição.

## Evidências complementares

### Recuperação

| Método | MRR de chunk | Context R@1 | R@3 | R@5 | R@10 |
|---|---:|---:|---:|---:|---:|
| BM25 | 0,470 | 0,344 | 0,581 | 0,625 | 0,656 |
| Semântico | 0,496 | 0,369 | 0,563 | 0,631 | 0,744 |
| RRF | 0,531 | 0,419 | 0,606 | 0,656 | 0,744 |

Em k=5, o RRF cobriu o span de 105 das 160 perguntas respondíveis. Assim, 33,9% das 310
perguntas apresentaram evidência suficiente no contexto recuperado. “Não respondível”
significa ausência de resposta anotada entre os Technotes candidatos oficiais, não
impossibilidade universal.

### Comparação global dos sinais

| Método | ROC-AUC | PR-AUC | AURC |
|---|---:|---:|---:|
| logística | 0,744 | 0,604 | 0,478 |
| BM25 top-1 | 0,503 | 0,346 | 0,663 |
| semântico top-1 | 0,628 | 0,450 | 0,574 |
| RRF top-1 | 0,720 | 0,504 | 0,546 |

Descritivamente, a logística apresentou os melhores três valores. Estatisticamente, os
IC95% pareados sustentaram as vantagens sobre BM25 e semântico em ROC-AUC, PR-AUC e AURC.
Contra RRF, sustentaram apenas ΔPR-AUC +0,100 [0,034; 0,172]; ΔROC-AUC +0,024
[−0,023; 0,067] e redução de AURC +0,068 [−0,005; 0,096] permaneceram inconclusivos.

Na política equilibrada, ocorreram 59 falsas autorizações e 35 abstenções indevidas. Entre
as falsas autorizações, 47 pertenciam à classe sem resposta anotada nos candidatos e 12 eram
misses de recuperação, mostrando que contextos tecnicamente plausíveis ainda recebem
confiança elevada.

## Conclusão, contribuição e limites

A hipótese recebe **apoio parcial**. Sinais leves e independentes do LLM melhoram a
ordenação dos casos de suficiência documental, sobretudo na faixa mais seletiva, mas não
demonstram superioridade uniforme sobre a recuperação híbrida nem garantem a transferência
segura de limiares entre distribuições.

A contribuição empírica consiste em avaliar um gate pré-geração leve e interpretável no
suporte técnico; compará-lo de forma pareada com BM25, semântico e RRF; localizar o ganho
nas menores coberturas; e mostrar que boa ordenação não assegura controle de risco por
limiares transferidos. A implicação de governança é que thresholds exigem validação local,
monitoramento e eventual recalibração antes de uso operacional.

O estudo não propõe inovação algorítmica da regressão, não avalia a correção da resposta de
um LLM e não demonstra prontidão para produção. A evidência provém de um único dataset, de
um holdout local com sobreposição conhecida de perguntas e de suficiência definida dentro
do universo documental do TechQA. Artefatos: `figures/final_test_v2/`,
`figures/fixed_coverage_v1/` e `docs/research_questions_evidence_matrix.md`.
