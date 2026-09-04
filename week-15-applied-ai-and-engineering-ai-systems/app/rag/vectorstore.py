"""Persistent Chroma vector store wrapper."""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional


class ChromaVectorStore:
    def __init__(self, persist_dir: str, collection_name: str):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        self._client = chromadb.PersistentClient(path=persist_dir, settings=ChromaSettings(anonymized_telemetry=False))
        self._collection = self._client.get_or_create_collection(collection_name)

    def add_documents(self, chunks: List[str], embeddings, source: str, doc_id: Optional[str] = None) -> str:
        doc_id = doc_id or str(uuid.uuid4())
        ids = [f"{doc_id}::{i}" for i in range(len(chunks))]
        metadatas: List[Dict] = [{"source": source, "doc_id": doc_id, "chunk_index": i} for i in range(len(chunks))]
        self._collection.add(ids=ids, documents=chunks, embeddings=embeddings.tolist(), metadatas=metadatas)
        return doc_id

    def query(self, query_embedding, k: int = 4):
        return self._collection.query(query_embeddings=[query_embedding.tolist()], n_results=k)

    def count(self) -> int:
        return self._collection.count()
