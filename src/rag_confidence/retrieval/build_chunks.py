"""Build an immutable tokenizer-aware chunk corpus for all canonical documents."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import transformers
import yaml
from transformers import AutoTokenizer

from rag_confidence.data.audit import sha256_file
from rag_confidence.retrieval.chunking import chunk_document
from rag_confidence.runtime import configure_system_trust_store


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed-dir", type=Path, default=Path("data/processed/techqa_v1"))
    parser.add_argument("--config", type=Path, default=Path("configs/retrieval.yaml"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/interim/chunks_bge_v1"))
    parser.add_argument("--model-cache", type=Path, default=Path("data/interim/model_cache"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_system_trust_store()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite chunk corpus: {output_dir}")
    building_dir = output_dir.with_name(f"{output_dir.name}.building")
    if building_dir.exists():
        raise FileExistsError(f"Stale partial chunk corpus requires inspection: {building_dir}")

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    semantic = config["semantic"]
    chunking = config["chunking"]
    tokenizer = AutoTokenizer.from_pretrained(
        semantic["model"],
        revision=semantic["revision"],
        cache_dir=args.model_cache.resolve(),
        use_fast=True,
    )
    if not getattr(tokenizer, "is_fast", False):
        raise RuntimeError("A fast tokenizer is required for character offsets")

    documents_path = args.processed_dir.resolve() / "documents.parquet"
    documents = pd.read_parquet(documents_path)
    building_dir.mkdir(parents=True, exist_ok=False)
    chunks_path = building_dir / "chunks.parquet"
    records: list[dict[str, object]] = []
    writer: pq.ParquetWriter | None = None
    chunk_count = 0
    maximum_input_tokens = 0
    for row in documents.itertuples(index=False):
        document_chunks = chunk_document(
            tokenizer,
            str(row.document_id),
            str(row.title),
            str(row.text),
            body_size_tokens=int(chunking["body_size_tokens"]),
            overlap_tokens=int(chunking["overlap_tokens"]),
            title_max_tokens=int(chunking["title_max_tokens"]),
            model_max_length=int(tokenizer.model_max_length),
        )
        records.extend(chunk.to_record() for chunk in document_chunks)
        chunk_count += len(document_chunks)
        maximum_input_tokens = max(
            maximum_input_tokens,
            max(chunk.input_token_count for chunk in document_chunks),
        )
        if len(records) >= 2_000:
            table = pa.Table.from_pylist(records)
            if writer is None:
                writer = pq.ParquetWriter(chunks_path, table.schema, compression="zstd")
            writer.write_table(table)
            records.clear()
    if records:
        table = pa.Table.from_pylist(records)
        if writer is None:
            writer = pq.ParquetWriter(chunks_path, table.schema, compression="zstd")
        writer.write_table(table)
        records.clear()
    if writer is None:
        raise RuntimeError("No chunks were generated")
    writer.close()
    chunk_config = {
        "model": semantic["model"],
        "revision": semantic["revision"],
        "model_max_length": int(tokenizer.model_max_length),
        **chunking,
    }
    config_hash = hashlib.sha256(
        json.dumps(chunk_config, sort_keys=True).encode("utf-8")
    ).hexdigest()
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config": chunk_config,
        "config_sha256": config_hash,
        "transformers": transformers.__version__,
        "documents": int(len(documents)),
        "chunks": chunk_count,
        "maximum_input_tokens": maximum_input_tokens,
        "source_documents_sha256": sha256_file(documents_path),
        "chunks_sha256": sha256_file(chunks_path),
    }
    (building_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    building_dir.rename(output_dir)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
