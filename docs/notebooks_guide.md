# Guia dos notebooks

Os notebooks são a camada narrativa e visual da pesquisa. Eles não são a
implementação principal e não devem ser usados para selecionar novamente
modelos, limiares ou coberturas.

| Notebook | Finalidade | Fonte principal |
|---|---|---|
| `01_data_audit.ipynb` | Inspecionar esquema, splits, candidatos e duplicações | `data/manifests/` e `docs/data_audit.md` |
| `02_results_exploration.ipynb` | Explorar tabelas e erros internos | `results/runs/` |
| `03_confidence_analysis.ipynb` | Visualizar scores, calibração e risco | artefatos de confiança congelados |
| `04_hard_negative_audit.ipynb` | Examinar negativos difíceis e conflitos técnicos | `docs/hard_negative_audit.md` |
| `05_prevalence_sensitivity.ipynb` | Visualizar a sensibilidade a prevalências | `docs/prevalence_sensitivity.md` |
| `06_final_results.ipynb` | Visualizar o holdout já executado | `docs/final_results.md` e JSONs finais |
| `07_fixed_coverage_risk.ipynb` | Explorar risco em coberturas fixas | `docs/fixed_coverage_risk.md` |

Ao abrir um notebook, execute primeiro a célula de contexto e confirme os
caminhos dos artefatos. As figuras devem ser regeneradas em uma pasta de saída
identificada, sem substituir os arquivos finais sem registro. Resultados
numéricos devem ser lidos dos CSVs/JSONs, nunca digitados manualmente.
