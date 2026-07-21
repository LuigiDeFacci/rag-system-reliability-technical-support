# Texto-base de resultados para o TCC

**Estado:** avaliação final congelada concluída; texto factual pronto para transcrição e revisão acadêmica.

Este arquivo receberá somente fatos derivados de execuções registradas, com referência ao `run_id`, configuração e versão dos dados. Hipóteses, expectativas e decisões de projeto não serão apresentadas como achados.

## Evidências documentais já verificadas

O release auditado contém 600 perguntas de treino, das quais 450 respondíveis, e 310 de desenvolvimento, das quais 160 respondíveis. Cada pergunta possui aproximadamente 50 Technotes candidatos. Foram encontrados 28.482 documentos únicos no arquivo compartilhado por treino e desenvolvimento.

Todos os spans de treino reproduzem exatamente o trecho delimitado no documento. Onze casos de desenvolvimento apresentam diferenças entre o trecho e o campo textual `ANSWER`, embora possuam documento e offsets válidos. A inspeção identificou diferenças de formatação, respostas textuais vazias com regiões válidas e um caso de evidência indicada por região mais ampla.

A auditoria identificou 22 textos de pergunta idênticos entre treino e desenvolvimento e 49 pares com similaridade TF-IDF igual ou superior a 0,90, incluindo os exatos. Por isso, a avaliação reportará tanto o desenvolvimento oficial quanto análises sem sobreposição de perguntas.

## Seções reservadas

1. Caracterização dos dados auditados.
2. Desempenho da recuperação.
3. Discriminação e calibração.
4. Risco e cobertura.
5. Ablations e análises por cenário.
6. Análise de erros.
7. Implicações gerenciais e limitações.

## Resultado preliminar do baseline lexical

O BM25 documental foi executado somente nas subdivisões internas do treino. Na seleção, obteve MRR de 0,553, Recall@1 de 0,500 e Recall@10 de 0,656 entre as 90 perguntas respondíveis. O run `20260721-002321_bm25-doc_5c311f59` não acessou o desenvolvimento oficial. Esses números constituem referência preliminar e não permitem aceitar ou rejeitar a hipótese do estudo.

## Comparação preliminar em nível de chunk

Com a segmentação v1 comum, o recall de contexto na seleção interna foi, respectivamente em
@1/@3/@5/@10: BM25 0,411/0,467/0,478/0,578; semântico
0,333/0,522/0,600/0,644; RRF 0,411/0,500/0,522/0,622. O RRF apresentou o maior MRR do
primeiro chunk que contém integralmente o span (0,475), mas o semântico apresentou maior
recall de contexto em @3, @5 e @10. Portanto, esta etapa indica complementaridade, sem
demonstrar superioridade uniforme da fusão. O teste final permanece fechado.

## Mecanismo de confiança na seleção interna

O mecanismo foi treinado com 22 sinais previamente fixados e avaliado em 120 perguntas na
seleção interna. Em k=5, 47 contextos (39,2%) continham evidência suficiente. A regressão
logística bruta obteve ROC-AUC 0,864, PR-AUC 0,793, Brier 0,148, ECE-10 0,098 e AURC
discreta 0,348. Platt e isotônica apresentaram Brier de 0,162 e 0,154, respectivamente; por
isso, não foram mantidos no protocolo candidato.

No mesmo conjunto, os sinais top-1 do BM25, semântico e RRF obtiveram ROC-AUC de 0,604,
0,714 e 0,766, e AURC de 0,546, 0,451 e 0,448. No bootstrap pareado agrupado por pergunta,
com 2.000 réplicas, a vantagem da logística sobre RRF foi 0,098 em ROC-AUC (IC95%
0,022–0,170), 0,199 em PR-AUC (0,091–0,332) e 0,100 de redução da AURC
(0,014–0,189). Esses resultados são internos e ainda não testam a generalização.

O limiar equilibrado de 0,429 produziu cobertura de 40,0%, risco seletivo de 20,8%, precisão
0,792, recall 0,809 e F1 0,800. Houve dez falsos positivos — oito em misses naturais de
recuperação — e nove falsos negativos. Na ablação, o conjunto completo liderou ROC-AUC e
F1; o subconjunto semântico foi marginalmente superior em PR-AUC e AURC. Portanto, os
achados preliminares apoiam a comparação final, mas não autorizam aceitar a hipótese antes
do protocolo congelado e do holdout.

## Estresse preliminar com negativos difíceis

Foram construídos 1.350 contextos internos após remover o documento gold e selecionar os
cinco primeiros chunks não-gold de BM25, semântico e RRF. Entre os 90 contextos híbridos da
seleção, a confiança média caiu de 0,488 no contexto natural para 0,340 no contexto sem o
gold; a diferença pareada média foi −0,149 (IC95% −0,199 a −0,101). A confiança diminuiu em
66,7% das perguntas.

Mesmo com a queda média, o ponto equilibrado autorizou incorretamente 25,6% dos negativos
difíceis (IC95% 16,7%–34,4%). As políticas conservadora e expansiva autorizaram 7,8% e
31,1%, respectivamente. Como o conjunto foi artificialmente construído com 100% de
negativos, esses valores medem falsa autorização sob estresse e não representam calibração,
prevalência real ou risco de produção.

## Sensibilidade à prevalência

Ao reponderar a seleção interna para prevalências positivas de 20%, 40%, 60% e 80%, sem
reajustar o modelo, o ECE-10 foi 0,194, 0,097, 0,132 e 0,237. O risco do ponto equilibrado
foi 40,4%, 20,3%, 10,1% e 4,1%, respectivamente. Na prevalência de 20%, o IC95% do risco
foi 23,9%–52,5%. A variação confirma que a calibração e a política são condicionais à
distribuição avaliada e não devem ser interpretadas como probabilidades universais.

## Resultado final congelado

O run final `20260721-024728_final-test-k5_68bd89db` foi executado com a especificação
congelada, sem refit ou recalibração.

No desenvolvimento oficial, a recuperação RRF cobriu o span em 65,6% das 160 perguntas
respondíveis em k=5, contra 62,5% do BM25 e 63,1% do semântico. O mecanismo de confiança
obteve ROC-AUC 0,744, PR-AUC 0,604, Brier 0,195, ECE-10 0,082 e AURC 0,478 nas 310
perguntas. As análises sem duplicatas exatas e sem flags de quase duplicata apresentaram
ROC-AUC 0,742 e 0,738, respectivamente.

Na política equilibrada congelada, cobertura foi 41,6%, risco 45,7%, precisão 0,543, recall
0,667 e F1 0,598. Foram observadas 59 falsas autorizações — 47 perguntas nativamente não
respondíveis e 12 misses — e 35 abstenções indevidas. A política conservadora, embora
selecionada internamente para risco ≤10%, apresentou risco final de 35,7% com cobertura de
13,5%, evidenciando mudança de distribuição e ausência de garantia operacional.

Em comparação ao RRF top-1, a logística melhorou PR-AUC em 0,100 (IC95% 0,034–0,172). A
diferença de ROC-AUC foi 0,024 (−0,023–0,067) e a redução de AURC foi 0,068
(−0,005–0,096), ambas com intervalos incluindo zero. Contra BM25 e semântico, os intervalos
das três métricas favoreceram a logística. Conclui-se que a hipótese recebeu apoio parcial:
a combinação melhora a identificação de positivos em relação aos sinais isolados, mas não
demonstrou superioridade uniforme sobre RRF nem estabilidade suficiente dos riscos para uso
direto como política de produção.
