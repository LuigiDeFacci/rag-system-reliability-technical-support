# Registro de decisões

Decisões são imutáveis por identificador. Alterações criam uma nova entrada que substitui explicitamente a anterior.

| ID | Estado | Decisão | Justificativa |
|---|---|---|---|
| D001 | aceita | Usar a pasta atual como raiz do projeto, sem mover o DOCX ou as referências. | Evita quebrar o material acadêmico existente. |
| D002 | aceita | Não alterar o manuscrito sem pedido explícito. | O DOCX é a especificação científica principal. |
| D003 | aceita | Manter código reutilizável em `src/`; notebooks ficam para auditoria e visualização. | Reprodutibilidade e testabilidade. |
| D004 | aceita | Tratar resultados naturais da recuperação como análise principal e cenários artificiais como estresse. | Evita que artefatos sintéticos definam a tarefa. |
| D005 | aceita | Bloquear o teste até o congelamento do protocolo e exigir `--allow-test`. | Previne ajuste retrospectivo. |
| D006 | aceita | Não versionar dados sem licença verificada. | Preparação para publicação aberta responsável. |
| D007 | provisória | Usar RRF como primeira fusão híbrida. | Evita somar diretamente escalas incompatíveis. |
| D008 | provisória | Usar Brier Score como métrica primária de calibração e ECE como complementar. | O ECE depende do esquema de bins. |
| D009 | aceita | Usar o desenvolvimento oficial como holdout final local e subdividir o treino oficial, com agrupamento, para ajuste, calibração e seleção. | O leaderboard foi descontinuado e não há rótulos do teste cego no release. |
| D010 | aceita | Reranquear os candidatos oficiais na análise principal; deixar o corpus completo como secundário. | A respondibilidade negativa só é válida no universo anotado. |
| D011 | aceita | Deduplicar IDs documentais dentro de cada lista candidata, preservando ordem, e registrar a transformação. | Duas perguntas de desenvolvimento repetem o documento gold. |
| D012 | aceita | Tratar `validation/` apenas como smoke test. | As 20 perguntas são cópias exatas das primeiras 20 de desenvolvimento. |
| D013 | aceita | Reportar desenvolvimento oficial, `dev_clean` sem duplicatas exatas de treino e análise agrupada secundária. | Há 22 perguntas idênticas entre treino e desenvolvimento. |
| D014 | aceita | Licenciar e atribuir os dados sob CDLA-Permissive-1.0, separadamente do código. | É a licença incluída no arquivo oficial. |
| D015 | aceita | Dividir o treino em 360/120/120 por atribuição gulosa estratificada e agrupada. | Mantém grupos juntos e prevalência 75/25 idêntica nos três subconjuntos. |
| D016 | aceita | Fixar o primeiro BM25 em nível documental com `k1=1,2`, `b=0,75`, título + texto e tokenizer técnico. | Estabelece um baseline transparente antes de chunking ou tuning. |
| D017 | aceita | Usar `BAAI/bge-small-en-v1.5` na revisão `5c38ec7...` como primeiro retriever semântico. | É leve, em inglês, MIT, possui instrução de consulta documentada e já aparece no material de referência. |
| D018 | provisória | Segmentar com 448 tokens de corpo, overlap 128 e até 56 tokens de título. | Respeita 512 tokens, preserva identificadores no título e cobre 438/450 spans internos em um único chunk. |
| D019 | aceita | Avaliar suficiência no contexto top-k de chunks e reportar presença documental separadamente. | Spans longos podem exigir a união de chunks; presença do documento não garante evidência no trecho enviado ao gerador. |
| D020 | aceita | Fixar o host de execução em Python 3.10.2, PyTorch 2.11.0+cu128 e lock específico de Windows/CUDA. | Python 3.14 não era compatível; a GPU reduziu a projeção de embeddings em aproximadamente nove vezes. |
| D021 | aceita | Ignorar no Git o DOCX do TCC, PDFs de referência e notebooks copiados do curso. | São insumos locais com termos de redistribuição distintos; o repositório público conterá apenas código e documentação autoral. |
| D022 | aceita | Usar exclusivamente o split interno `selection` para escolher k e thresholds. | Corrige a nomenclatura antiga `validation` e mantém `calibration` separado do ajuste e da seleção. |

## Ambiguidades abertas

| ID | Questão | Critério de resolução |
|---|---|---|
| A004 | A configuração v1 é suficiente para a comparação principal? | Comparar cobertura contextual apenas nos splits internos; congelar antes do teste final. |
| A005 | resolvida por D020 | Manter locks específicos por plataforma quando houver wheels distintos do PyTorch. |
| A006 | Qual licença aplicar ao código do repositório? | Escolha do autor antes da publicação; dados terão termos separados. |
| A007 | Como tratar os 11 spans divergentes do desenvolvimento? | Revisão manual registrada antes de congelar o rótulo de chunk. |
| A008 | Quais quase duplicatas representam o mesmo caso? | Revisão manual da triagem TF-IDF; não excluir automaticamente. |
