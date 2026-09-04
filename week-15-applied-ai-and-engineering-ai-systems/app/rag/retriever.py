from __future__ import annotations

from typing import List

from pydantic import BaseModel


class RetrievedChunk(BaseModel):
    text: str
    source: str
    score: float


class Retriever:
    def __init__(self, embedding_model, vector_store):
        self._embeddings = embedding_model
        self._store = vector_store

    def retrieve(self, query: str, k: int = 4) -> List[RetrievedChunk]:
        if self._store.count() == 0:
            return []
        query_vec = self._embeddings.embed([query])[0]
        raw = self._store.query(query_vec, k=k)
        results: List[RetrievedChunk] = []
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, distances):
            score = max(0.0, 1.0 - dist)  # chroma returns cosine distance -> similarity
            results.append(RetrievedChunk(text=doc, source=meta.get("source", "unknown"), score=round(score, 4)))
        return results
