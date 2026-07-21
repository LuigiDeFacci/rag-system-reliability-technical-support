# Revisão das instruções de implementação

**Data:** 20 de julho de 2026.

## Mantido como regra

- Auditar arquivos, licença e esquema antes de definir o protocolo final.
- Separar perguntas antes de qualquer derivação e agrupar tudo por `query_id`.
- Impedir uso do teste em seleção, calibração ou exploração.
- Proibir features gold ou indisponíveis em produção.
- Manter o LLM fora do resultado mínimo.
- Começar por baselines simples e regressão logística interpretável.
- Ajustar transformações apenas no treino e calibrar em dados separados.
- Usar bootstrap agrupado por pergunta e comparações pareadas.
- Registrar configurações, hashes, ambiente e artefatos imutáveis por run.
- Não publicar dados, credenciais ou índices sem autorização compatível.

## Ajustado

1. **Negativos:** resultados naturais da recuperação serão a análise principal. Negativos aleatórios, difíceis construídos e conflitos técnicos serão testes de estresse. Isso evita que o mecanismo de criação de cenários defina artificialmente a tarefa.
2. **Teste final:** “executar uma vez” significa não modificar o protocolo depois de observar o resultado. Reruns idênticos para auditoria ou reprodução são permitidos e registrados.
3. **Calibração:** Brier Score será central; ECE será complementar e terá bins documentados. Regressão isotônica será avaliada com cautela devido à pequena amostra esperada.
4. **nDCG:** será usado apenas se a auditoria confirmar uma noção de relevância adequada. Com relevância binária e um único documento gold, Recall@k e MRR podem ser mais informativos.
5. **Teste oficial:** o artigo descreve 490 perguntas de avaliação cega, mas o repositório oficial informa que o leaderboard foi descontinuado. Após auditoria, a estratégia provável é reservar o desenvolvimento oficial como holdout local final e subdividir o treino oficial para ajuste, calibração e seleção. Ele não será chamado de teste oficial.
6. **Corpus:** a decisão entre corpus completo e os 50 candidatos oficiais foi adiada. O artigo informa que o documento-resposta podia ser inserido artificialmente entre os candidatos, uma ameaça que precisa ser considerada.

## Confirmado nos arquivos reais

O release contém casos respondíveis e não respondíveis, answer spans, 50 candidatos por pergunta na quase totalidade dos casos e metadados estruturados de produto. O conjunto de validação técnica não é independente do desenvolvimento. A licença incluída é CDLA-Permissive-1.0, distinta da licença Apache-2.0 do código da IBM.

## Adiado até haver dados ou ambiente validado

- modelo e revisão dos embeddings;
- estratégia de chunking;
- k principal;
- normalização das pontuações;
- taxonomia final dos cenários secundários;
- ferramenta de ambiente e lockfile;
- licença do código aberto;
- disponibilidade e mecanismo de avaliação do teste oficial.
