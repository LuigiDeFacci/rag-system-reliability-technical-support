# Checklist de substituição dos capítulos 8–10

Este checklist orienta a transcrição futura para o `.docx`. Ele não autoriza alteração do
manuscrito nem mudança no experimento congelado.

## Antes de editar o manuscrito

- [ ] Ativar controle de alterações no Word e criar uma cópia versionada do manuscrito.
- [ ] Remover dos capítulos 8–10 frases prospectivas como “será descrito”, “serão
  apresentados” e “não há resultados experimentais”.
- [ ] Usar “desenvolvimento oficial empregado como holdout final local”, nunca “teste cego
  oficial”, para as 310 perguntas.
- [ ] Definir “não respondível” como ausência de resposta anotada nos candidatos oficiais.
- [ ] Preservar a conclusão “apoio parcial” e qualificar diferenças cujo IC95% inclui zero.

## Capítulo 8 — Descrição do caso

- [ ] Substituir o plano de descrição pelos quatro primeiros parágrafos de
  `docs/tcc_results_draft.md`, seção 8: composição do TechQA, escopo do rótulo, auditoria de
  duplicatas e configuração congelada.
- [ ] Inserir tabela de caracterização: treino 600 (450/150), desenvolvimento 310 (160/150),
  cerca de 50 candidatos e 28.482 Technotes únicos. Fonte: `docs/data_audit.md`.
- [ ] Citar Castelli et al. (2020) na descrição do TechQA e conferir a entrada completa na
  bibliografia.
- [ ] Inserir tabela de recuperação BM25/semântico/RRF em R@1/3/5/10 e MRR. Fonte:
  `figures/final_test_v2/retrieval_metrics.csv`.
- [ ] Explicar que k=5 e o RRF foram congelados antes do holdout; não narrar essa escolha
  como otimização posterior.

## Capítulo 9 — Análise do caso

- [ ] Abrir o capítulo respondendo diretamente à pergunta principal com ROC-AUC 0,744,
  PR-AUC 0,604, Brier 0,195, ECE-10 0,082 e AURC 0,478.
- [ ] Inserir como evidência principal a tabela de risco em coberturas fixas da seção 9.2,
  incluindo casos respondidos, quatro métodos e os Δriscos logística−BM25,
  logística−semântico e logística−RRF com IC95%.
- [ ] Após a tabela, registrar inclusão fracionária de empates, bootstrap por `query_id`,
  2.000 réplicas pareadas e seed 42.
- [ ] Separar explicitamente: vantagem descritiva até 40%; ausência de diferença de risco
  sustentada contra RRF; ganho de PR-AUC sustentado contra RRF.
- [ ] Inserir tabela das políticas congeladas com respostas, encaminhamentos, cobertura e
  risco; destacar como achado que o risco conservador de ≤10% interno não foi preservado e
  atingiu 35,7% no holdout, sem atribuir causalmente a diferença.
- [ ] Qualificar os 2,3% como diagnóstico retrospectivo do holdout, não novo limiar nem
  política validada.
- [ ] Inserir a análise curta da matriz `[[146,59],[35,70]]` e dos 59 falsos positivos.
- [ ] Inserir a seção 9.4 de diálogo com as cinco fontes primárias verificadas.
- [ ] Usar as figuras na ordem abaixo e atualizar numeração, título, fonte e chamada no texto:
  - [ ] `figures/fixed_coverage_v1/fixed_coverage_risk.png` — evidência principal.
  - [ ] `figures/final_test_v2/reliability_final.png` — calibração.
  - [ ] `figures/final_test_v2/risk_coverage_final.png` — visão contínua complementar.
  - [ ] `figures/final_test_v2/confusion_balanced_final.png` — erros da política.
  - [ ] `figures/final_test_v2/scenario_probabilities_final.png` — opcional, se não repetir a
    análise textual.

## Capítulo 10 — Conclusões

- [ ] Substituir integralmente os parágrafos condicionais pela conclusão central da seção 10
  de `docs/tcc_results_draft.md`.
- [ ] Declarar “apoio parcial”, sem alegar inovação algorítmica, confirmação plena ou
  prontidão para produção.
- [ ] Inserir uma única seção de contribuição empírica: gate leve pré-geração, comparação
  justa, ganho concentrado nas menores coberturas e falha de transferência dos limiares.
- [ ] Inserir uma única seção de governança: validação local, monitoramento, versionamento e
  eventual recalibração dos thresholds.
- [ ] Inserir uma única seção de limitações: um dataset, holdout local, duplicatas conhecidas,
  universo documental restrito e ausência de avaliação do gerador.
- [ ] Manter continuidade futura separada de resultados observados.

## Conferência final

- [ ] Conferir todos os números contra `docs/research_questions_evidence_matrix.md`.
- [ ] Conferir citações e acrescentar as cinco referências da consolidação à bibliografia.
- [ ] Verificar que toda tabela e figura é citada antes de aparecer e contém “Fonte:
  elaboração própria”.
- [ ] Atualizar sumário automático, numeração de quadros/tabelas/figuras e referências
  cruzadas.
- [ ] Executar revisão ortográfica em português e abrir o DOCX final em um segundo viewer.
