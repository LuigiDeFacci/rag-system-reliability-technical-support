# Protocolo de pesquisa

**Versão:** 0.2 — provisória após auditoria inicial  
**Data:** 20 de julho de 2026  
**Estado:** não congelado; proibida a avaliação final em teste.

## Pergunta e hipótese

**Pergunta:** a combinação de sinais de recuperação lexical e semântica permite estimar, de forma calibrada, quando um sistema RAG possui evidência suficiente para responder a perguntas de suporte técnico?

**Hipótese:** em níveis comparáveis de cobertura, uma regressão logística calibrada que combine pontuações, margens, dispersão e concordância entre retrievers apresentará menor risco seletivo do que limiares aplicados isoladamente ao BM25, ao retriever semântico ou à recuperação híbrida.

O desfecho é a autorização para responder, não a correção geral de uma resposta gerada. O LLM fica fora do experimento principal.

## Unidade e rótulo

A unidade experimental será uma pergunta e o contexto top-k produzido por uma configuração de recuperação. Todas as configurações derivadas da mesma `query_id` permanecerão no mesmo split.

O release confirma answer spans e relevância documental. O rótulo seguirá esta ordem:

1. Na avaliação de chunks, `y=1` quando o contexto contiver a região gold delimitada por offsets; caso contrário, `y=0`.
2. Na avaliação documental, a presença do documento gold será uma proxy explicitamente identificada.
3. Perguntas nativas não respondíveis terão `y=0` no universo dos candidatos oficiais, para o qual foram anotadas.

O rótulo nunca utilizará pontuações, ranks, concordância dos retrievers ou o tipo de cenário.

## Corpus e análise principal

O experimento principal reranqueará os 50 candidatos oficiais por pergunta. Essa escolha preserva a validade dos casos não respondíveis. O corpus completo poderá ser usado em análise secundária, mas não receberá automaticamente rótulos negativos, pois pode conter evidência não anotada fora dos candidatos.

A análise principal deve refletir o resultado natural da recuperação: o contexto é positivo ou negativo conforme contenha a evidência anotada. Remoções artificiais e negativos construídos serão usados como testes de estresse separados. Isso reduz o risco de o modelo aprender artefatos do gerador de cenários.

## Divisões e prevenção de vazamento

As divisões oficiais serão preservadas na análise principal. O treino será subdividido, agrupando textos idênticos, entre ajuste, calibração e seleção. O desenvolvimento oficial ficará bloqueado como holdout final. O diretório `validation/`, composto pelas primeiras 20 perguntas do desenvolvimento, será usado apenas como smoke test.

Foram encontrados 22 textos idênticos entre treino e desenvolvimento, além de candidatos a quase duplicata. Para comparabilidade, o desenvolvimento oficial completo será reportado. Como robustez, serão reportados um `dev_clean` sem duplicatas exatas de treino e uma divisão secundária agrupada. O holdout local nunca será apresentado como o teste oficial cego de 490 perguntas.

## Recuperação

Serão comparados BM25, recuperação semântica e fusão por Reciprocal Rank Fusion. Documentos candidatos duplicados serão removidos preservando a ordem original. Corpus, segmentação e valores de k serão idênticos. A segmentação v1 usa o tokenizer fixado do `BAAI/bge-small-en-v1.5` (revisão `5c38ec7...`), 448 tokens de corpo, overlap 128 e até 56 tokens de título. O ranking principal será de chunks; o ranking documental por máximo score será uma análise complementar. Serão avaliados k em `{1, 3, 5, 10}`, e o k principal será escolhido apenas na seleção interna do treino.

Recall@k e MRR serão calculados nas perguntas respondíveis. nDCG@k será reportado somente se acrescentar informação à relevância binária observada. A avaliação distinguirá recuperação de documento e de trecho.

## Variáveis e modelos

O conjunto inicial será pequeno e interpretável: top-1, média, dispersão e margem top-1/top-2 de cada retriever; sobreposição top-k; concordância do top-1; estatísticas de rank; tamanho da pergunta; e padrões observáveis de códigos ou versões. Transformações serão ajustadas apenas no treino.

Os métodos serão avaliados nesta ordem: limiar BM25, limiar semântico, limiar híbrido e regressão logística. Modelos mais complexos dependerão de justificativa posterior. Serão feitas ablações lexical, semântica, concordância e conjunto completo.

Serão comparadas probabilidades brutas, Platt Scaling e regressão isotônica. Como a isotônica pode sobreajustar em amostras pequenas, sua complexidade e estabilidade serão analisadas, não presumidas como superiores.

## Métricas e inferência

- Classificação: Precision, Recall, F1, ROC-AUC, PR-AUC e matriz de confusão.
- Calibração: Brier Score, ECE com bins documentados e diagrama de confiabilidade.
- Decisão seletiva: cobertura, risco entre casos aceitos, curva risco-cobertura, AURC, cobertura em riscos fixos e risco em coberturas fixas.
- Recuperação: Recall@k, MRR e, quando aplicável, nDCG@k.

Intervalos de confiança usarão bootstrap agrupado por `query_id`. Comparações serão pareadas pelas mesmas perguntas. Pontos conservador, equilibrado e expansivo serão definidos na validação por critérios registrados, não por limiares intuitivos.

## Congelamento e teste

Antes do teste final, devem estar congelados: versão dos dados, segmentação, k, variáveis, transformações, modelo, calibrador, limiares, métricas, gráficos previstos e código. A execução exigirá `--allow-test` e configuração com hashes. “Uma única vez” significa ausência de ajuste posterior ao resultado; reruns idênticos para verificação serão permitidos e registrados.

## Ameaças previstas

As principais ameaças são: pequena amostra; prevalência diferente entre treino (75% respondível) e desenvolvimento (51,6%); rótulo documental como proxy; 11 divergências entre spans e respostas em desenvolvimento; inserção do documento-resposta entre candidatos; duplicações entre splits; mudança de domínio; instabilidade do ECE; e distância entre abstenção experimental e encaminhamento humano real. A calibração será sempre descrita como válida para a distribuição avaliada.
