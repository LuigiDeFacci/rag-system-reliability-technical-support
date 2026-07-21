# Plano congelado de avaliação final

**Estado:** pronto para execução controlada; gate fechado.  
**Especificação:** `configs/final_test_spec.yaml`.

## Pré-condições

1. Worktree Git limpa e commit congelado registrado em `configs/final_test.yaml`.
2. Hash da especificação igual ao hash do gate.
3. Dados `techqa_v1`, chunks, embeddings e modelo com hashes já auditados.
4. Nenhum refit, recalibração, seleção de k, feature ou limiar após a abertura.

## Campanha única

Após um commit separado abrir o gate, executar BM25, semântico e RRF apenas em
`final_test`, todos com `--allow-test`. Em seguida, executar
`rag_confidence.evaluation.run_final_test` com os três runs e o modelo congelado. Cada
comando produz diretório imutável e manifesto `final_test_used=true`.

O avaliador verifica a especificação, o ancestral Git congelado, a limpeza do worktree, os
hashes dos dados e do modelo, o número esperado de 310 perguntas e o alinhamento dos três
rankings. As features são extraídas sem gold; só depois são unidas aos rótulos para métricas.

## Saídas predeterminadas

- Retrieval em k=1/3/5/10 para BM25, semântico e RRF.
- Discriminação, Brier, ECE-10 e AURC em k=5.
- Políticas conservadora, equilibrada e expansiva com limiares congelados.
- Comparações pareadas com baselines e 2.000 bootstraps por `query_id`.
- Desenvolvimento oficial, `dev_clean_exact` e `dev_clean_near`.
- Diagrama de confiabilidade, risco-cobertura, matriz equilibrada e distribuição por cenário.
- Análise de erros no ponto equilibrado.

Após a execução, o gate deve ser fechado novamente. Resultados inesperados serão explicados,
não usados para reabrir escolhas. Reexecução só é aceitável para falha técnica ou verificação
idêntica, com registro no `test_access_log.md`.
