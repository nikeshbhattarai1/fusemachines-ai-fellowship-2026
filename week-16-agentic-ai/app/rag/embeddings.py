from __future__ import annotations

from typing import List


class EmbeddingModel:
    def __init__(self, model_name: str):
        self._model_name = model_name
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # local import

            self._model = SentenceTransformer(self._model_name)

    def embed(self, texts: List[str]):
        import numpy as np

        self._ensure_loaded()
        return np.asarray(self._model.encode(texts, normalize_embeddings=True))
