"""Encode the immutable chunk corpus with the pinned semantic retriever."""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sentence_transformers
import torch
import yaml
from sentence_transformers import SentenceTransformer

from rag_confidence.data.audit import sha256_file
from rag_confidence.runtime import configure_system_trust_store


def select_device(requested: str) -> str:
    if requested == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is unavailable to PyTorch")
    return requested


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks-dir", type=Path, default=Path("data/interim/chunks_bge_v1"))
    parser.add_argument("--config", type=Path, default=Path("configs/retrieval.yaml"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/interim/embeddings_bge_v1"))
    parser.add_argument("--model-cache", type=Path, default=Path("data/interim/model_cache"))
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_system_trust_store()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite embeddings: {output_dir}")
    if args.batch_size <= 0:
        raise ValueError("batch-size must be positive")

    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    semantic = config["semantic"]
    chunks_path = args.chunks_dir.resolve() / "chunks.parquet"
    chunks_manifest_path = args.chunks_dir.resolve() / "manifest.json"
    chunks = pd.read_parquet(chunks_path)
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("limit must be positive")
        chunks = chunks.iloc[: args.limit].copy()

    device = select_device(args.device)
    model = SentenceTransformer(
        semantic["model"],
        revision=semantic["revision"],
        cache_folder=str(args.model_cache.resolve()),
        device=device,
    )
    started = datetime.now(timezone.utc)
    start_clock = time.perf_counter()
    embeddings = model.encode(
        chunks["passage_text"].tolist(),
        batch_size=args.batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=bool(semantic["normalize_embeddings"]),
    ).astype(np.float32, copy=False)
    elapsed = time.perf_counter() - start_clock
    if embeddings.ndim != 2 or len(embeddings) != len(chunks):
        raise RuntimeError("Embedding output shape does not match the chunk corpus")

    output_dir.mkdir(parents=True, exist_ok=False)
    embeddings_path = output_dir / "chunk_embeddings.npy"
    index_path = output_dir / "chunk_index.parquet"
    np.save(embeddings_path, embeddings, allow_pickle=False)
    chunks.drop(columns=["passage_text"]).to_parquet(index_path, index=False, compression="zstd")
    source_manifest = json.loads(chunks_manifest_path.read_text(encoding="utf-8"))
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "started_at_utc": started.isoformat(),
        "model": semantic["model"],
        "revision": semantic["revision"],
        "license": semantic["license"],
        "normalize_embeddings": bool(semantic["normalize_embeddings"]),
        "device": device,
        "batch_size": args.batch_size,
        "benchmark_limit": args.limit,
        "rows": int(embeddings.shape[0]),
        "dimensions": int(embeddings.shape[1]),
        "elapsed_seconds": elapsed,
        "rows_per_second": len(embeddings) / elapsed,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "sentence_transformers": sentence_transformers.__version__,
        "chunk_config_sha256": source_manifest["config_sha256"],
        "source_chunks_sha256": sha256_file(chunks_path),
        "artifacts": {
            "chunk_embeddings": sha256_file(embeddings_path),
            "chunk_index": sha256_file(index_path),
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
