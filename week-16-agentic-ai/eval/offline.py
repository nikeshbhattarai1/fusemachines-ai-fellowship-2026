"""Builds AgentSources backed by the lexical retriever (no embedding model / network needed)."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from app.agent.faults import FaultSpec, FaultyAgentSources
from app.agent.sources import AgentSources, FactsRegistry, SourceCatalog
from app.rag.lexical import LexicalRetriever

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIRS = [ROOT / "data" / "sample_docs", ROOT / "data" / "corpus"]


def load_corpus_docs() -> dict:
    return {p.name: p.read_text(encoding="utf-8") for d in CORPUS_DIRS for p in sorted(d.glob("*.md"))}


def build_offline_sources(fault: Optional[str] = None, fault_sleep: Optional[float] = None,
                          chunk_size: int = 350, overlap: int = 40) -> Any:
    src = AgentSources(LexicalRetriever(load_corpus_docs(), chunk_size, overlap),
                       FactsRegistry(str(ROOT / "data" / "facts" / "facts.json")),
                       SourceCatalog(str(ROOT / "data" / "corpus" / "manifest.json")))
    spec = FaultSpec.parse(fault)
    if spec is None:
        return src
    if fault_sleep is not None:
        spec.sleep_seconds = fault_sleep
    return FaultyAgentSources(src, spec)
