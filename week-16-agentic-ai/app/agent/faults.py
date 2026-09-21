from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from app.agent.errors import ToolUnavailable

MODES = {"unavailable", "malformed", "timeout"}
TOOL_TO_METHOD = {"kb_search": "search", "facts_lookup": "lookup_facts", "list_sources": "list_sources"}


@dataclass
class FaultSpec:
    mode: str
    tool: str
    sleep_seconds: float = 30.0   # only used by "timeout"

    @staticmethod
    def parse(text: Optional[str]) -> Optional["FaultSpec"]:
        if not text:
            return None
        try:
            mode, tool = text.split(":", 1)
        except ValueError as exc:
            raise ValueError(f"Bad fault spec {text!r}; expected '<mode>:<tool>'") from exc
        if mode not in MODES or tool not in TOOL_TO_METHOD:
            raise ValueError(f"Bad fault spec {text!r}; modes={sorted(MODES)}, tools={sorted(TOOL_TO_METHOD)}")
        return FaultSpec(mode=mode, tool=tool)

    def __str__(self) -> str:
        return f"{self.mode}:{self.tool}"


_GARBAGE = {
    "search": {"results": "N/A"},                        # not a list of passages
    "lookup_facts": "<html>502 Bad Gateway</html>",      # not a dict
    "list_sources": 42,                                  # not a list
}


class FaultyAgentSources:
    """Wraps an AgentSources and misbehaves for exactly one tool."""

    def __init__(self, inner: Any, spec: FaultSpec):
        self._inner = inner
        self.spec = spec
        self.injected_calls = 0

    def __getattr__(self, name: str) -> Any:  # source_names(), meta_for(), ... pass straight through
        return getattr(self._inner, name)

    def _apply(self, method: str, fn: Callable[..., Any], *a: Any, **kw: Any) -> Any:
        if TOOL_TO_METHOD[self.spec.tool] != method:
            return fn(*a, **kw)
        self.injected_calls += 1
        if self.spec.mode == "unavailable":
            raise ToolUnavailable(f"{self.spec.tool} backend unreachable (injected fault)")
        if self.spec.mode == "timeout":
            time.sleep(self.spec.sleep_seconds)
            return fn(*a, **kw)
        return _GARBAGE[method]  # malformed

    def search(self, *a: Any, **kw: Any) -> Any:
        return self._apply("search", self._inner.search, *a, **kw)

    def lookup_facts(self, *a: Any, **kw: Any) -> Any:
        return self._apply("lookup_facts", self._inner.lookup_facts, *a, **kw)

    def list_sources(self, *a: Any, **kw: Any) -> Any:
        return self._apply("list_sources", self._inner.list_sources, *a, **kw)
