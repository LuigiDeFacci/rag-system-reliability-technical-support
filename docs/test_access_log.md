# Registro de acesso ao holdout final

O desenvolvimento oficial do TechQA é o holdout final local. Este arquivo registra todo
acesso aos seus rótulos, inclusive auditorias sem avaliação de modelo.

| Data | Acesso | Motivo | Efeito sobre decisões |
|---|---|---|---|
| 2026-07-20 | Esquema, contagens, candidatos, documentos, offsets, duplicatas e divergências de spans | Auditoria obrigatória antes de formalizar o protocolo | Definiu a interpretação dos campos, o bloqueio do holdout e análises de sensibilidade; nenhuma pontuação de modelo foi produzida. |
| 2026-07-20 | Verificação estrutural de contenção dos 160 spans respondíveis na segmentação v1 | Validar integridade dos offsets após gerar chunks | 157 spans cabem em um chunk. A configuração já estava fixada e não foi alterada com esse resultado. O dado não será usado para selecionar segmentação, k, features ou thresholds. |

O comando de avaliação continua bloqueado em `configs/final_test.yaml`. Auditorias futuras
devem ser acrescentadas aqui antes da abertura formal do teste.
