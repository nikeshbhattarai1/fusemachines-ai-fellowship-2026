from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    text: str
    source: str
    score: float


class Retriever:
    def __init__(self, embedding_model, vector_store):
        self._embeddings = embedding_model
        self._store = vector_store

    def sources(self) -> List[str]:
        return self._store.list_sources()

    def retrieve(self, query: str, k: int = 4, source: Optional[str] = None) -> List[RetrievedChunk]:
        if self._store.count() == 0:
            return []
        query_vec = self._embeddings.embed([query])[0]
        raw = self._store.query(query_vec, k=k, where={"source": source} if source else None)
        results: List[RetrievedChunk] = []
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, distances):
            results.append(RetrievedChunk(text=doc, source=meta.get("source", "unknown"), score=round(self._similarity(dist), 4)))
        return results

    def _similarity(self, dist: float) -> float:
        """Distance -> cosine similarity in [0, 1].

        Bug fixed in W16: this used `1 - dist` unconditionally, but Chroma's default metric is squared L2, where
        (for the L2-normalised embeddings we use) dist = 2 - 2*cos. The old score was therefore 2*cos - 1, clamped
        at 0: every passage with cosine <= 0.5 looked like zero relevance. The conversion now follows the
        collection's actual metric, so it is right for existing collections too (no re-ingest needed).
        """
        space = self._store.space() if hasattr(self._store, "space") else "cosine"
        sim = 1.0 - dist / 2.0 if space == "l2" else 1.0 - dist
        return max(0.0, min(1.0, sim))
