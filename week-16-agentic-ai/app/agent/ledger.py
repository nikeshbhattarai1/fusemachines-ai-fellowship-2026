from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

_WS = re.compile(r"\s+")
_TRANSLATE = str.maketrans(
    {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "*": None, "`": None}
)


def normalize_text(text: str) -> str:
    """Case/whitespace/markdown-insensitive form used for quote matching."""
    return _WS.sub(" ", text.translate(_TRANSLATE)).strip().lower()


@dataclass
class Evidence:
    id: str
    source: str
    kind: str                 # document | structured | calc
    text: str
    score: Optional[float] = None
    meta: Dict[str, str] = field(default_factory=dict)
    query: str = ""
    step: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EvidenceLedger:
    def __init__(self, max_entries: int = 20, snippet_chars: Optional[int] = 600):
        self.max_entries = max_entries
        # None = keep full text (raw ablation mode)
        self.snippet_chars = snippet_chars
        self._items: Dict[str, Evidence] = {}
        self._keys: Dict[str, str] = {}
        self._counter = 0
        self.sources_attempted: Set[str] = set()

    # writing 
    def add(
        self,
        *,
        source: str,
        kind: str,
        text: str,
        score: Optional[float] = None,
        meta: Optional[Dict[str, str]] = None,
        query: str = "",
        step: int = 0,
    ) -> Tuple[Optional[Evidence], str]:
        """Returns (evidence, status) with status in {"added", "duplicate", "dropped_cap"}."""
        clean = _WS.sub(" ", text).strip()
        meta = dict(meta or {})
        if self.snippet_chars and len(clean) > self.snippet_chars:
            clean = clean[: self.snippet_chars].rsplit(" ", 1)[0]
            meta["truncated"] = "true"
        key = f"{source}|{hashlib.sha1(normalize_text(clean).encode()).hexdigest()[:12]}"
        if key in self._keys:
            return self._items[self._keys[key]], "duplicate"
        if len(self._items) >= self.max_entries:
            return None, "dropped_cap"
        self._counter += 1
        ev = Evidence(
            id=f"E{self._counter}", source=source, kind=kind, text=clean, score=score, meta=meta, query=query, step=step
        )
        self._items[ev.id] = ev
        self._keys[key] = ev.id
        return ev, "added"

    def mark_attempted(self, source: str) -> None:
        self.sources_attempted.add(source)

    # reading
    def get(self, evidence_id: str) -> Optional[Evidence]:
        return self._items.get(evidence_id)

    def items(self) -> List[Evidence]:
        return list(self._items.values())

    def __len__(self) -> int:
        return len(self._items)

    def distinct_sources(self, ids: Iterable[str]) -> Set[str]:
        return {self._items[i].source for i in ids if i in self._items}

    def dump(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._items.values()]

    def render(self) -> str:
        """Compact text block placed in the system prompt each iteration (managed mode)."""
        if not self._items:
            return "(empty -- no evidence gathered yet)"
        lines: List[str] = []
        for ev in self._items.values():
            head = f"[{ev.id}] {ev.source} ({ev.kind}"
            if ev.meta.get("last_updated"):
                head += f", updated {ev.meta['last_updated']}"
            if ev.score is not None:
                head += f", relevance {ev.score:.2f}"
            lines.append(head + ")")
            lines.append(f'    "{ev.text}"')
        return "\n".join(lines)
