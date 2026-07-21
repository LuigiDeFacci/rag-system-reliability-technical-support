# Registro de acesso ao holdout final

O desenvolvimento oficial do TechQA é o holdout final local. Este arquivo registra todo
acesso aos seus rótulos, inclusive auditorias sem avaliação de modelo.

| Data | Acesso | Motivo | Efeito sobre decisões |
|---|---|---|---|
| 2026-07-20 | Esquema, contagens, candidatos, documentos, offsets, duplicatas e divergências de spans | Auditoria obrigatória antes de formalizar o protocolo | Definiu a interpretação dos campos, o bloqueio do holdout e análises de sensibilidade; nenhuma pontuação de modelo foi produzida. |
| 2026-07-20 | Verificação estrutural de contenção dos 160 spans respondíveis na segmentação v1 | Validar integridade dos offsets após gerar chunks | 157 spans cabem em um chunk. A configuração já estava fixada e não foi alterada com esse resultado. O dado não será usado para selecionar segmentação, k, features ou thresholds. |
| 2026-07-20 | Autorização da campanha final, ainda sem execução | Protocolo v1 congelado no commit `0d76d05`, especificação SHA-256 `68bd89db...` | Gate aberto uma vez para os três retrievers e o avaliador congelado; nenhuma escolha poderá ser alterada com os resultados. |

O gate será fechado novamente imediatamente após a campanha. Qualquer falha ou reexecução
deve ser acrescentada aqui antes de nova abertura.
