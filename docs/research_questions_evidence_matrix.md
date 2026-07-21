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
| O classificador combinado apresenta menor risco seletivo que BM25, semântico e RRF em coberturas comparáveis? | Hipótese principal de menor risco em coberturas fixas. | Risco em 10%, 20%, 40%, 60%, 80% e 100% de cobertura; bootstrap pareado por pergunta. | Contra RRF, Δrisco logística−RRF: −13,0; −9,8; −2,7; +0,4; +0,3; 0,0 pontos percentuais. A logística teve menor risco descritivo até 40%, mas não em 60% ou 80%. | IC95% dos Δ: [−28,7; 3,2], [−18,5; 2,7], [−8,9; 2,3], [−2,9; 4,3], [−2,0; 2,3] e [0,0; 0,0] p.p. | Houve vantagem descritiva na faixa mais seletiva e evidência favorável contra sinais isolados, mas nenhuma diferença de risco contra RRF foi estatisticamente sustentada nas coberturas fixas. | **Parcialmente sustentado** | `results/runs/20260721-122015_fixed-coverage_430de878/metrics.json`; `figures/fixed_coverage_v1/fixed_coverage_risk.csv` |
| Como diferentes tolerâncias ao risco afetam cobertura e necessidade de encaminhamento humano? | Descrever o compromisso gerencial entre resposta automática e abstenção, sem estimar produtividade ou ROI. | Aplicação dos três limiares congelados; cobertura, risco e número de decisões. | Conservadora: 42 respostas (13,5%), 268 encaminhamentos e risco 35,7%. Equilibrada: 129 (41,6%), 181 e 45,7%. Expansiva: 133 (42,9%), 177 e 46,6%. Risco observado ≤10% corresponderia a apenas 2,3%, cerca de 7 respostas. | Não calculado para os pontos gerenciais no protocolo congelado; os valores são descritivos do holdout. | Maior cobertura veio acompanhada de maior risco. Os nomes das políticas refletem a seleção interna e não constituem garantias no holdout. | **Sustentado** | `results/runs/20260721-024728_final-test-k5_68bd89db/metrics.json`; `docs/final_results.md` |

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

Os empates no score de fronteira foram tratados por **inclusão fracionária**: calcula-se o
risco esperado ao aceitar a fração necessária do grupo empatado, evitando que a ordem das
linhas determine o resultado. O bootstrap usou `query_id` como unidade de reamostragem,
2.000 réplicas pareadas e seed 42.

## Níveis de interpretação

### Superioridade descritiva

A logística apresentou ROC-AUC, PR-AUC e AURC numericamente melhores que os três baselines.
Em coberturas fixas, apresentou menor risco observado que o RRF em 10%, 20% e 40%, e risco
ligeiramente maior em 60% e 80%.

### Superioridade estatisticamente sustentada

Contra BM25 e semântico, os IC95% pareados de ROC-AUC, PR-AUC e redução de AURC ficaram
acima de zero. Contra RRF, apenas o ganho de PR-AUC foi sustentado; os intervalos de
ROC-AUC, AURC e de todas as diferenças de risco em coberturas fixas incluíram zero. Portanto,
não há base para afirmar superioridade uniforme sobre a recuperação híbrida.

### Interpretação gerencial

Cobertura representa a fração experimental de casos autorizados, e abstenção representa a
fração encaminhada para tratamento adicional ou humano. Não são medidas de produtividade,
custo ou ROI. O fracasso de transferência do limiar conservador é um achado: thresholds
precisam de validação local, monitoramento contínuo e eventual recalibração antes de qualquer
uso operacional.

## Conclusão central

Sinais leves e independentes do LLM melhoram a ordenação dos casos de suficiência
documental, sobretudo na faixa mais seletiva, mas não demonstram superioridade uniforme
sobre a recuperação híbrida nem garantem a transferência segura de limiares entre
distribuições.
