from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.llm.client import ProviderResponse, ToolCall

Step = Dict[str, Any]   # {"text": str?, "calls": [{"name": str, "input": dict}, ...]}


def call(name: str, **kwargs: Any) -> Dict[str, Any]:
    return {"name": name, "input": kwargs}


class ScriptedLLM:
    name = "scripted"

    def __init__(self, steps: List[Step], usage: Optional[Dict[str, int]] = None):
        self.steps = steps
        self.usage = usage            # None -> the loop estimates tokens and flags them as estimated
        self.i = 0
        self.seen_messages: List[List[Dict[str, Any]]] = []
        self.seen_tool_choice: List[Optional[str]] = []

    def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], temperature: float, top_p: float,
             max_tokens: int, tool_choice: Optional[str] = None) -> Tuple[ProviderResponse, str]:
        self.seen_messages.append([dict(m) for m in messages])
        self.seen_tool_choice.append(tool_choice)
        step = self.steps[min(self.i, len(self.steps) - 1)]
        self.i += 1
        calls = [ToolCall(id=f"call_{self.i}_{j}", name=c["name"], input=c["input"]) for j, c in enumerate(step.get("calls", []))]
        return ProviderResponse(stop_reason="tool_use" if calls else "end_turn", text=step.get("text", ""),
                                tool_calls=calls, usage=self.usage), self.name


class ExplodingLLM:
    """Every call fails, like an exhausted provider chain."""
    name = "exploding"

    def chat(self, *a: Any, **kw: Any):
        raise RuntimeError("All LLM providers failed or are unavailable. Last error: simulated outage")
