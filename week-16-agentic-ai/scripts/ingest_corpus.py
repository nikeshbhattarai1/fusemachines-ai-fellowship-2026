from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIRS = [ROOT / "data" / "sample_docs", ROOT / "data" / "corpus"]


def ensure_ingested(chunk_size: int = 350, overlap: int = 40, verbose: bool = True) -> List[str]:
    from app.dependencies import get_embedding_model, get_vector_store
    from app.rag.ingest import chunk_text

    store, embedder = get_vector_store(), get_embedding_model()
    present = set(store.list_sources())
    added: List[str] = []
    for d in CORPUS_DIRS:
        for path in sorted(d.glob("*.md")):
            if path.name in present:
                if verbose:
                    print(f"skip   {path.name} (already ingested)")
                continue
            chunks = chunk_text(path.read_text(encoding="utf-8"), chunk_size, overlap)
            store.add_documents(chunks, embedder.embed(chunks), source=path.name)
            added.append(path.name)
            if verbose:
                print(f"ingest {path.name}: {len(chunks)} chunks")
    return added


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chunk-size", type=int, default=350)
    ap.add_argument("--overlap", type=int, default=40)
    args = ap.parse_args()
    done = ensure_ingested(args.chunk_size, args.overlap)
    print(f"done: {len(done)} new document(s)")
