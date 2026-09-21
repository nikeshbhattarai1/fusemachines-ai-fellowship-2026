from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

FACTS_SOURCE = "facts_registry"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")


def _related(a: str, b: str) -> bool:
    return bool(a) and bool(b) and (a == b or (len(a) >= 4 and a in b) or (len(b) >= 4 and b in a))


class FactsRegistry:
    name = FACTS_SOURCE

    def __init__(self, path: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        if data is None:
            data = json.loads(Path(path).read_text(encoding="utf-8")) if path and Path(path).exists() else {}
        self._entities: Dict[str, Any] = data.get("entities", {})
        self.meta: Dict[str, Any] = data.get("_meta", {})

    def entities(self) -> List[str]:
        return sorted(self._entities)

    def lookup(self, entity: str, attribute: Optional[str] = None) -> Dict[str, Any]:
        qe, qa = _norm(entity), _norm(attribute) if attribute else ""
        matches: List[Dict[str, Any]] = []
        relaxed = False

        def emit(ename: str, aname: str, a: Dict[str, Any]) -> None:
            matches.append({
                "entity": ename, "attribute": aname, "value": a.get("value"), "unit": a.get("unit", ""),
                "last_updated": a.get("last_updated", self.meta.get("last_updated", "")),
                "source_of_truth": a.get("source_of_truth", ""),
            })

        for ename, e in self._entities.items():
            names = {_norm(ename)} | {_norm(x) for x in e.get("aliases", [])}
            if not any(_related(qe, n) for n in names):
                continue
            attrs = e.get("attributes", {})
            picked = {k: v for k, v in attrs.items() if not qa or _related(qa, _norm(k))}
            if qa and not picked:          # entity known, attribute wrong: show what exists
                picked, relaxed = attrs, True
            for aname, a in picked.items():
                emit(ename, aname, a)
        if not matches:                    # model may have passed an attribute-like phrase as the entity
            for ename, e in self._entities.items():
                for aname, a in e.get("attributes", {}).items():
                    if _related(qe, _norm(aname)):
                        emit(ename, aname, a)
        out: Dict[str, Any] = {"matches": matches, "known_entities": self.entities()}
        if relaxed:
            out["note"] = "Attribute not found for that entity; all its attributes are listed."
        return out


class SourceCatalog:
    """Manifest with per-source metadata (kind, last_updated, authority)."""

    def __init__(self, path: Optional[str] = None):
        self._data: Dict[str, Any] = {}
        if path and Path(path).exists():
            self._data = {k: v for k, v in json.loads(Path(path).read_text(encoding="utf-8")).items() if not k.startswith("_")}

    def meta(self, name: str) -> Dict[str, Any]:
        return self._data.get(name, {})


class AgentSources:
    """Facade the tool runner talks to. Every method may raise; the runner turns that into a tool error."""

    def __init__(self, retriever: Any, facts: FactsRegistry, catalog: SourceCatalog):
        self._retriever, self._facts, self._catalog = retriever, facts, catalog

    def search(self, query: str, source: Optional[str] = None, k: int = 4) -> List[Dict[str, Any]]:
        return [c.model_dump() for c in self._retriever.retrieve(query, k=k, source=source)]

    def lookup_facts(self, entity: str, attribute: Optional[str] = None) -> Dict[str, Any]:
        return self._facts.lookup(entity, attribute)

    def list_sources(self) -> List[Dict[str, Any]]:
        out = []
        for name in self.source_names():
            m = self._catalog.meta(name)
            out.append({
                "name": name,
                "kind": m.get("kind", "structured" if name == FACTS_SOURCE else "document"),
                "last_updated": m.get("last_updated", "unknown"),
                "authority": m.get("authority", "unknown"),
                "description": m.get("description", ""),
            })
        return out

    # used internally by the loop (never fault-injected)
    def source_names(self) -> List[str]:
        docs = self._retriever.sources() if hasattr(self._retriever, "sources") else []
        return list(docs) + [FACTS_SOURCE]

    def meta_for(self, name: str) -> Dict[str, Any]:
        return self._catalog.meta(name)
