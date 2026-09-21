from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List, Optional

from app.rag.ingest import chunk_text
from app.rag.retriever import RetrievedChunk

_STOP = {
    "the", "a", "an", "of", "to", "in", "is", "are", "for", "and", "or", "on", "at", "by", "with", "it", "its",
    "what", "which", "how", "does", "do", "did", "this", "that", "be", "as", "from", "than", "then", "was", "were",
    "many", "much", "long", "per", "each",
}


def _tokens(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP]


class LexicalRetriever:
    def __init__(self, docs: Dict[str, str], chunk_size: int = 350, overlap: int = 40):
        self._chunks: List[dict] = []
        for source, text in docs.items():
            for chunk in chunk_text(text, chunk_size, overlap):
                toks = _tokens(chunk)
                self._chunks.append({"source": source, "text": chunk, "tf": Counter(toks), "len": len(toks) or 1})
        n = max(1, len(self._chunks))
        df: Counter = Counter()
        for c in self._chunks:
            df.update(c["tf"].keys())
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        self._avg = sum(c["len"] for c in self._chunks) / n

    def sources(self) -> List[str]:
        return sorted({c["source"] for c in self._chunks})

    def count(self) -> int:
        return len(self._chunks)

    def retrieve(self, query: str, k: int = 4, source: Optional[str] = None) -> List[RetrievedChunk]:
        q = [t for t in _tokens(query)]
        if not q:
            return []
        scored = []
        for c in self._chunks:
            if source and c["source"] != source:
                continue
            s = 0.0
            for t in set(q):
                tf = c["tf"].get(t, 0)
                if tf:
                    s += self._idf.get(t, 0.0) * (tf * 2.2) / (tf + 1.2 * (0.25 + 0.75 * c["len"] / self._avg))
            if s > 0:
                scored.append((s, c))
        if not scored:
            return []
        ceiling = sum(self._idf.get(t, 0.0) * 2.2 for t in set(q)) or 1.0
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            RetrievedChunk(text=c["text"], source=c["source"], score=round(min(1.0, s / ceiling), 4))
            for s, c in scored[:k]
        ]
