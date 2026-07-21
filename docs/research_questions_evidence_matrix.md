# Matriz de perguntas de pesquisa e evidências

## Escopo da consolidação

As respostas abaixo usam o desenvolvimento oficial do TechQA como **holdout final local**
de 310 perguntas. Ele não é o teste cego oficial de 490 perguntas. Nenhum resultado desta
matriz provocou retreinamento, recalibração ou alteração de features, modelos, limiares,
coberturas ou métodos estatísticos.

## Matriz principal

| Pergunta de pesquisa | Hipótese ou objetivo correspondente | Métrica ou análise | Resultado numérico no holdout | Intervalo de confiança | Resposta obtida | Situação | Arquivo-fonte |
|---|---|---|---|---|---|---|---|
| A combinação de sinais lexicais e semânticos permite estimar, de forma calibrada, quando há evidência suficiente para responder? | Avaliar um gate pré-geração leve, interpretável e independente do LLM. | ROC-AUC, PR-AUC, Brier, ECE-10 e AURC; comparação pareada com sinais top-1. | Logística: ROC-AUC 0,744; PR-AUC 0,604; Brier 0,195; ECE-10 0,082; AURC 0,478. | Contra RRF: ΔROC-AUC +0,024 [−0,023; 0,067]; ΔPR-AUC +0,100 [0,034; 0,172]; redução de AURC +0,068 [−0,005; 0,096]. | Sim para ordenação probabilística, com ressalvas: houve discriminação útil e ganho de PR-AUC, mas sobreconfiança nas faixas altas e baixa transferência dos limiares. | **Parcialmente sustentado** | `results/runs/20260721-024728_final-test-k5_68bd89db/metrics.json`; `docs/final_results.md` |
| O classificador combinado apresenta menor risco seletivo que BM25, semântico e RRF em coberturas comparáveis? | Hipótese principal de menor risco em coberturas fixas. | Risco em 10%, 20%, 40%, 60%, 80% e 100% de cobertura; bootstrap pareado por pergunta. | A logística teve menor risco descritivo que BM25 e semântico em 10%–80%; contra RRF, somente em 10%–40%. | O IC95% de logística−BM25 excluiu zero em 10%–80%; logística−semântico, em 40% e 60%; logística−RRF, em nenhuma cobertura parcial. | Há sustentação em risco fixo contra BM25 e, pontualmente, contra semântico. Não há sustentação uniforme contra semântico nem RRF. | **Parcialmente sustentado** | `results/runs/20260721-122015_fixed-coverage_430de878/metrics.json`; `figures/fixed_coverage_v1/fixed_coverage_risk_reductions.csv` |
| Como diferentes tolerâncias ao risco afetam cobertura e necessidade de encaminhamento humano? | Descrever o compromisso gerencial entre resposta automática e abstenção, sem estimar produtividade ou ROI. | Aplicação dos três limiares congelados; cobertura, risco e número de decisões. | Conservadora: 42 respostas (13,5%), 268 encaminhamentos e risco 35,7%. Equilibrada: 129 (41,6%), 181 e 45,7%. Expansiva: 133 (42,9%), 177 e 46,6%. Retrospectivamente, risco observado ≤10% ocorreu em 2,3% do holdout, cerca de 7 respostas. | Não calculado para os pontos gerenciais no protocolo congelado; os valores são descritivos do holdout. | Maior cobertura veio acompanhada de maior risco. Os nomes das políticas refletem a seleção interna e não constituem garantias. Os 2,3% são diagnóstico retrospectivo, não novo limiar ou política validada. | **Sustentado** | `results/runs/20260721-024728_final-test-k5_68bd89db/metrics.json`; `docs/final_results.md` |

## Evidência principal em coberturas fixas

Define-se Δrisco como `risco(logística) − risco(RRF)`; valores negativos favorecem a
logística.

| Cobertura | Casos respondidos (aprox.) | Risco logística | Risco BM25 | Risco semântico | Risco RRF | Δrisco logística−RRF | IC95% do Δ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10% | 31 | 32,3% | 64,5% | 51,6% | 45,3% | −13,0 p.p. | [−28,7; 3,2] |
| 20% | 62 | 35,5% | 66,1% | 50,0% | 45,3% | −9,8 p.p. | [−18,5; 2,7] |
| 40% | 124 | 45,2% | 66,1% | 56,5% | 47,9% | −2,7 p.p. | [−8,9; 2,3] |
| 60% | 186 | 53,8% | 64,0% | 60,8% | 53,3% | +0,4 p.p. | [−2,9; 4,3] |
| 80% | 248 | 60,1% | 65,7% | 62,5% | 59,7% | +0,3 p.p. | [−2,0; 2,3] |
| 100% | 310 | 66,1% | 66,1% | 66,1% | 66,1% | 0,0 p.p. | [0,0; 0,0] |

### Diferenças pareadas de risco fixo

| Cobertura | Logística−BM25 (IC95%) | Logística−semântico (IC95%) | Logística−RRF (IC95%) |
|---:|---:|---:|---:|
| 10% | −32,3 [−58,1; −12,9] p.p. | −19,4 [−38,7; 3,2] p.p. | −13,0 [−28,7; 3,2] p.p. |
| 20% | −30,6 [−43,5; −16,1] p.p. | −14,5 [−25,8; 0,0] p.p. | −9,8 [−18,5; 2,7] p.p. |
| 40% | −21,0 [−30,6; −13,7] p.p. | −11,3 [−19,4; −4,0] p.p. | −2,7 [−8,9; 2,3] p.p. |
| 60% | −10,2 [−16,1; −5,4] p.p. | −7,0 [−11,3; −1,6] p.p. | +0,4 [−2,9; 4,3] p.p. |
| 80% | −5,6 [−8,9; −2,8] p.p. | −2,4 [−5,6; 0,4] p.p. | +0,3 [−2,0; 2,3] p.p. |
| 100% | 0,0 [0,0; 0,0] p.p. | 0,0 [0,0; 0,0] p.p. | 0,0 [0,0; 0,0] p.p. |

Os empates no score de fronteira foram tratados por **inclusão fracionária**: calcula-se o
risco esperado ao aceitar a fração necessária do grupo empatado, evitando que a ordem das
linhas determine o resultado. O bootstrap usou `query_id` como unidade de reamostragem,
2.000 réplicas pareadas e seed 42.

## Níveis de interpretação

### Superioridade descritiva

A logística apresentou ROC-AUC, PR-AUC e AURC numericamente melhores que os três baselines.
Em coberturas fixas, teve menor risco observado que BM25 e semântico em 10%–80%. Contra
RRF, teve menor risco em 10%–40% e risco ligeiramente maior em 60% e 80%.

### Superioridade estatisticamente sustentada

Em **risco fixo**, os IC95% sustentaram menor risco da logística contra BM25 em 10%–80% e
contra semântico em 40% e 60%; não sustentaram diferença contra RRF. Separadamente, nas
**métricas globais**, ROC-AUC, PR-AUC e redução de AURC favoreceram de forma sustentada a
logística contra BM25 e semântico. Contra RRF, apenas o ganho de PR-AUC foi sustentado;
ROC-AUC e AURC foram inconclusivos. Portanto, evidência global não deve ser descrita como
evidência de menor risco em cada cobertura.

### Interpretação gerencial

Cobertura representa a fração experimental de casos autorizados, e abstenção representa a
fração encaminhada para tratamento adicional ou humano. Não são medidas de produtividade,
custo ou ROI. O limiar selecionado internamente não preservou seu nível de risco no holdout.
Isso não identifica causalmente o motivo, mas indica que a política é potencialmente
sensível à distribuição. Thresholds precisam de validação local, monitoramento contínuo e
eventual recalibração antes de qualquer uso operacional. A cobertura de 2,3% para risco
observado ≤10% é um diagnóstico retrospectivo do holdout; não representa um novo limiar
selecionado nem uma política validada.

## Conclusão central

Sinais leves e independentes do LLM melhoram a ordenação dos casos de suficiência
documental, sobretudo na faixa mais seletiva, mas não demonstram superioridade uniforme
sobre a recuperação híbrida nem garantem a transferência segura de limiares entre
distribuições.
