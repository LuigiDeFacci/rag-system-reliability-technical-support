# Recuperação semântica

## Modelo fixado

O retriever inicial é `BAAI/bge-small-en-v1.5`, revisão
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, licença MIT. A escolha é adequada ao
corpus em inglês, tem dimensão 384 e limite de 512 tokens, e coincide com o modelo usado
nos notebooks de referência do curso. Perguntas recebem o prefixo recomendado
`Represent this sentence for searching relevant passages: `; passagens não recebem prefixo.
Embeddings são normalizados e comparados por produto escalar, equivalente ao cosseno.

Fontes primárias: [model card](https://huggingface.co/BAAI/bge-small-en-v1.5) e
[FlagEmbedding](https://github.com/FlagOpen/FlagEmbedding).

## Segmentação v1

Cada documento é dividido com o tokenizer fixado do modelo: 448 tokens de corpo,
overlap de 128 e até 56 tokens de título. O código reduz a janela quando necessário e
preserva offsets de caracteres no corpo original. O artefato local contém 90.284 chunks
para 28.461 documentos; nenhum input excede 510 tokens.

Nos 450 casos respondíveis dos splits internos, 438 spans cabem integralmente em um único
chunk: 263/270 em `fit`, 88/90 em `calibration` e 87/90 em `selection`. A mediana do span é
65 wordpieces, o percentil 95 é 254 e o máximo é 545. A suficiência do contexto top-k será
calculada também pela união dos intervalos recuperados; presença do documento gold será
reportada apenas como proxy de sensibilidade.

## Ambiente e benchmark

O host usa uma `.venv` Python 3.10.2 porque a instalação principal 3.14 não é suportada
pela pilha PyTorch no Windows. `truststore` integra HTTPS ao repositório de certificados do
Windows, sem desabilitar validação TLS. O benchmark CPU codificou 256 chunks em 53,72 s
(4,77 chunks/s), projetando cerca de 5h15 para o corpus. A build CUDA 12.8 na GTX 1650,
com batch 32, processou a mesma amostra em 5,88 s (43,57 chunks/s), reduzindo a projeção
para aproximadamente 35 minutos.

Artefatos locais ficam em `data/interim/` e não são versionados. Manifestos registram
hashes do corpus, revisão do modelo, versões, dispositivo, batch size e desempenho.
