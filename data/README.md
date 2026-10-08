# Dados

Os dados do TechQA não estão presentes neste repositório. Antes de adicioná-los localmente:

1. confirme os termos de acesso, uso e redistribuição;
2. salve arquivos originais sem alteração em `data/raw/`;
3. registre origem, data de aquisição e SHA-256 em um manifesto;
4. nunca edite arquivos brutos em place;
5. gere derivados em `data/interim/`, `data/processed/` e `data/manifests/`.

Os dados brutos, intermediários e processados são ignorados pelo Git, exceto pelos
marcadores que preservam a estrutura. Em `data/manifests/`, resumos JSON selecionados são
versionados para documentar a auditoria e os resultados; os manifestos completos locais
continuam fora do Git. O repositório público contém instruções de obtenção e verificação,
sem cópia do corpus.
