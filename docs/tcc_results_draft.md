# Texto-base dos capítulos 8–10

**Estado:** consolidação científica pós-hoc das execuções congeladas. Este documento não
altera o protocolo nem o manuscrito `.docx` e deve ser revisado conforme as normas de estilo
e referência da instituição antes da transcrição.

**Rastreabilidade:** run final `20260721-024728_final-test-k5_68bd89db`; análise pós-hoc de
coberturas fixas `20260721-122015_fixed-coverage_430de878`; especificação SHA-256
`68bd89db...`.

## 8. Descrição do caso

O TechQA auditado contém 600 perguntas de treino, sendo 450 respondíveis, e 310 perguntas
de desenvolvimento, sendo 160 respondíveis no universo dos Technotes candidatos. O
desenvolvimento oficial foi reservado como holdout final local; ele não corresponde ao teste
cego oficial de 490 perguntas. A expressão “não respondível” indica que os anotadores não
encontraram resposta entre os aproximadamente 50 documentos candidatos, não que a pergunta
seja universalmente impossível de responder. O dataset e sua finalidade para question
answering técnico foram apresentados por Castelli et al. (2020).

O arquivo compartilhado por treino e desenvolvimento contém 28.482 Technotes únicos. A
auditoria encontrou 22 perguntas com texto idêntico entre treino e desenvolvimento e 49
pares com similaridade TF-IDF de pelo menos 0,90, incluindo os exatos. Por isso, o resultado
principal foi acompanhado por sensibilidades sem duplicatas exatas e sem flags de quase
duplicação; os respectivos ROC-AUC foram 0,742 e 0,738, próximos ao valor principal de
0,744.

BM25, recuperação semântica com `BAAI/bge-small-en-v1.5` e RRF operaram sobre o mesmo
corpus segmentado. O contexto principal foi fixado em k=5 antes do holdout. O rótulo foi
positivo somente quando o contexto continha integralmente a evidência anotada; scores de
recuperação não participaram de sua definição.

| Método | MRR de chunk | Context R@1 | R@3 | R@5 | R@10 |
|---|---:|---:|---:|---:|---:|
| BM25 | 0,470 | 0,344 | 0,581 | 0,625 | 0,656 |
| Semântico | 0,496 | 0,369 | 0,563 | 0,631 | 0,744 |
| RRF | 0,531 | 0,419 | 0,606 | 0,656 | 0,744 |

Em k=5, o RRF cobriu a evidência de 105 das 160 perguntas respondíveis. Dessa forma, 105
das 310 observações do holdout, ou 33,9%, continham evidência documental suficiente no
contexto efetivamente fornecido ao gate.

## 9. Análise do caso

### 9.1 Resposta à pergunta principal

A combinação de sinais permitiu estimar suficiência documental com capacidade de ordenação
útil, mas não com segurança operacional suficiente. A regressão logística obteve ROC-AUC
0,744, PR-AUC 0,604, Brier 0,195, ECE-10 0,082 e AURC 0,478. O diagrama de confiabilidade
revelou sobreconfiança nas faixas mais altas. Assim, a resposta à pergunta principal é
positiva com ressalvas: o mecanismo separa casos relativamente melhores e piores, mas a
probabilidade e os limiares não devem ser interpretados como garantias invariantes.

### 9.2 Hipótese em coberturas comparáveis

A evidência principal é o risco em coberturas fixas. Define-se Δrisco como
`risco(logística) − risco(RRF)`; valores negativos favorecem a logística.

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

Em risco fixo, os IC95% sustentaram menor risco da logística contra BM25 em 10%–80% e contra
o semântico em 40% e 60%. Contra o semântico em 10%, 20% e 80%, houve somente vantagem
descritiva. Contra RRF, a logística teve menor risco descritivo em 10%, 20% e 40%, mas todos
os IC95% parciais incluíram zero; em 60% e 80%, o RRF foi descritivamente ligeiramente
melhor. Empates na fronteira foram tratados por inclusão fracionária, correspondente ao
risco esperado de aceitar apenas a fração necessária do grupo empatado. O bootstrap usou a
pergunta (`query_id`) como unidade, 2.000 reamostragens pareadas e seed 42.

Nas métricas globais, a logística apresentou ROC-AUC, PR-AUC e AURC numericamente melhores
que BM25, semântico e RRF. Os intervalos pareados sustentaram as vantagens sobre BM25 e
semântico nas três métricas. Contra RRF, apenas o ganho de PR-AUC de 0,100, IC95%
[0,034; 0,172], foi sustentado; o ganho de ROC-AUC de 0,024 [−0,023; 0,067] e a redução de
AURC de 0,068 [−0,005; 0,096] permaneceram inconclusivos. Portanto, a hipótese recebe
**apoio parcial**, e não confirmação plena.

### 9.3 Tolerância ao risco e encaminhamento

| Política congelada | Respostas | Encaminhamentos | Cobertura | Risco |
|---|---:|---:|---:|---:|
| conservadora | 42 | 268 | 13,5% | 35,7% |
| equilibrada | 129 | 181 | 41,6% | 45,7% |
| expansiva | 133 | 177 | 42,9% | 46,6% |

O ponto conservador foi escolhido internamente para risco de até 10%, mas alcançou 35,7%
no holdout. Retrospectivamente, risco observado de até 10% ocorreu nos primeiros 2,3% do
holdout, cerca de sete perguntas. Essa cobertura é um diagnóstico retrospectivo do holdout;
não representa um novo limiar selecionado nem uma política validada. O resultado demonstra
apenas que o limiar interno não
preservou seu nível de risco no holdout; não identifica causalmente o motivo. A política pode
ser sensível à distribuição. Cobertura e encaminhamento são proxies experimentais; não
medem produtividade, custo ou retorno financeiro.

Na política equilibrada, a matriz de confusão foi `[[146,59],[35,70]]`, com 59 falsas
autorizações e 35 abstenções indevidas. Entre as falsas autorizações, 47 eram perguntas sem
resposta anotada nos candidatos oficiais e 12 eram falhas de recuperação. O gate reduz a
confiança de casos insuficientes em média, mas ainda aceita contextos tecnicamente
plausíveis sem a evidência necessária.

### 9.4 Diálogo com a literatura

Joren et al. (2025) distinguem erros causados por contexto insuficiente daqueles em que o
gerador deixa de usar evidência disponível e exploram suficiência para geração seletiva. O
presente estudo adota a mesma separação conceitual, mas mede, antes da geração, a presença da
evidência anotada no contexto de suporte técnico e não avalia a resposta do LLM
([OpenReview](https://openreview.net/forum?id=Jjr2Odj8DJ)).

SURE-RAG trata suficiência como propriedade do conjunto de evidências e agrega relações
entre uma resposta candidata e os trechos para decidir entre suporte, refutação e
insuficiência. Aqui, o gate é binário, precede qualquer resposta candidata e utiliza apenas
sinais leves dos retrievers; portanto, não substitui a verificação semântica proposta por
Qiu, Han e Huang (2026) ([arXiv](https://arxiv.org/abs/2605.03534)).

Geissler et al. (2026) combinam seleção conformal de chunks e um classificador de factualidade
baseado em atenção para estimar a consistência da resposta gerada com o contexto. Este
trabalho não oferece garantia conformal nem classifica factualidade da resposta: estima
suficiência documental pré-geração e mostra empiricamente que a transferência de limiares
pode falhar ([arXiv](https://arxiv.org/abs/2605.05244)).

Chen et al. (2024) controlam risco por prompting contrafactual, fazendo o próprio modelo
avaliar a qualidade da recuperação e o uso do contexto. O mecanismo aqui avaliado exclui o
LLM do gate e, por isso, testa uma alternativa de menor acoplamento e custo, sem alegar
superioridade direta entre desenhos que usam variáveis e tarefas diferentes
([ACL Anthology](https://aclanthology.org/2024.findings-emnlp.133/)).

Kamath, Jia e Liang (2020) mostram que probabilidades do modelo de QA podem ser
sobreconfiantes sob mudança de domínio e estudam calibradores treinados com dados fora do
domínio. O resultado atual é convergente quanto à fragilidade da abstenção sob mudança de
distribuição, mas o alvo é distinto: suficiência da evidência recuperada, e não correção da
resposta de um modelo de QA ([ACL Anthology](https://aclanthology.org/2020.acl-main.503/)).

## 10. Conclusões do estudo

Sinais leves e independentes do LLM melhoram a ordenação dos casos de suficiência
documental, sobretudo na faixa mais seletiva, mas não demonstram superioridade uniforme
sobre a recuperação híbrida nem garantem a transferência segura de limiares entre
distribuições.

### 10.1 Contribuição empírica

A contribuição consiste na avaliação de um gate pré-geração leve, interpretável e
independente do LLM no domínio de suporte técnico; na comparação pareada com BM25,
recuperação semântica e RRF; na identificação de que o ganho se concentra nas menores
coberturas; e na demonstração de que boa ordenação não garante controle de risco por
limiares transferidos. A regressão logística é um instrumento conhecido, não uma inovação
algorítmica proposta pelo estudo.

### 10.2 Implicação de governança

O limiar de confiança deve ser tratado como política organizacional potencialmente sensível
à distribuição. Antes de uso operacional, thresholds exigem validação local, monitoramento
da prevalência e da calibração, registro de versões e eventual recalibração. O mecanismo
avaliado não está pronto para autorizar respostas em produção.

### 10.3 Limitações e continuidade

As conclusões se limitam a um dataset de suporte técnico, a um holdout local de 310
perguntas com sobreposição conhecida em relação ao treino e a uma definição de
respondibilidade restrita aos candidatos oficiais. O experimento avalia suficiência do
contexto, não factualidade ou utilidade da resposta gerada. Estudos futuros devem testar
outros domínios, períodos e prevalências, preferencialmente com validação temporal ou
externa, e só então investigar recalibração e integração com um gerador.

## Referências citadas nesta consolidação

- CASTELLI, Vittorio et al. The TechQA Dataset. In: Proceedings of the 58th Annual Meeting
  of the Association for Computational Linguistics. 2020. p. 1269–1278. DOI:
  10.18653/v1/2020.acl-main.117. Disponível em:
  https://aclanthology.org/2020.acl-main.117/. Acesso em: 21 jul. 2026.

- CHEN, Lu et al. Controlling Risk of Retrieval-augmented Generation: A Counterfactual
  Prompting Framework. In: Findings of EMNLP 2024. p. 2380–2393. DOI:
  10.18653/v1/2024.findings-emnlp.133. Disponível em:
  https://aclanthology.org/2024.findings-emnlp.133/. Acesso em: 21 jul. 2026.
- GEISSLER, Florian et al. Towards Dependable Retrieval-Augmented Generation Using Factual
  Confidence Prediction. arXiv:2605.05244, 2026. Preprint. Disponível em:
  https://arxiv.org/abs/2605.05244. Acesso em: 21 jul. 2026.
- JOREN, Hailey et al. Sufficient Context: A New Lens on Retrieval Augmented Generation
  Systems. In: ICLR 2025. OpenReview: Jjr2Odj8DJ. Disponível em:
  https://openreview.net/forum?id=Jjr2Odj8DJ. Acesso em: 21 jul. 2026.
- KAMATH, Amita; JIA, Robin; LIANG, Percy. Selective Question Answering under Domain Shift.
  In: Proceedings of ACL 2020. p. 5684–5696. DOI: 10.18653/v1/2020.acl-main.503.
  Disponível em: https://aclanthology.org/2020.acl-main.503/. Acesso em: 21 jul. 2026.
- QIU, Jingxi; HAN, Zeyu; HUANG, Cheng. SURE-RAG: Sufficiency and Uncertainty-Aware Evidence
  Verification for Selective Retrieval-Augmented Generation. arXiv:2605.03534, 2026.
  Preprint. Disponível em: https://arxiv.org/abs/2605.03534. Acesso em: 21 jul. 2026.
