# Texto-base de resultados para o TCC

**Estado:** auditoria concluída; resultados internos preliminares; teste final não executado.

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
