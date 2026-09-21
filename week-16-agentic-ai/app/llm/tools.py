from __future__ import annotations

import ast
import datetime as dt
import operator
from typing import Any, Dict

# Tool schemas
RAG_SEARCH_TOOL: Dict[str, Any] = {
    "name": "rag_search",
    "description": "Search the ingested knowledge base for passages relevant to a query.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "k": {"type": "integer", "description": "Number of results to return", "default": 4},
        },
        "required": ["query"],
    },
}

CALCULATOR_TOOL: Dict[str, Any] = {
    "name": "calculator",
    "description": "Evaluate a basic arithmetic expression, e.g. '(3 + 4) * 2 / 7'.",
    "input_schema": {
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"],
    },
}

CURRENT_TIME_TOOL: Dict[str, Any] = {
    "name": "current_time",
    "description": "Return the current UTC date and time in ISO 8601 format.",
    "input_schema": {"type": "object", "properties": {}},
}

EMIT_ANSWER_TOOL: Dict[str, Any] = {
    "name": "emit_answer",
    "description": "Emit the final structured answer to the user. Must be called exactly once, as the last step.",
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "sources": {"type": "array", "items": {"type": "string"}},
            "used_tools": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["answer", "confidence"],
    },
}

ALL_TOOLS = [RAG_SEARCH_TOOL, CALCULATOR_TOOL, CURRENT_TIME_TOOL, EMIT_ANSWER_TOOL]

# Safe calculator (AST-restricted, no eval/exec)

_ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
        return _ALLOWED_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Unsupported or unsafe expression")


def calculate(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")
    return _safe_eval(tree.body)


class ToolExecutor:
    """
    Dispatches tool calls to their implementations.
    """

    def __init__(self, retriever) -> None:
        self._retriever = retriever

    def execute(self, name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        if name == "rag_search":
            results = self._retriever.retrieve(tool_input["query"], k=tool_input.get("k", 4))
            return {"results": [r.model_dump() for r in results]}
        if name == "calculator":
            try:
                return {"result": calculate(tool_input["expression"])}
            except Exception as exc:  # noqa: BLE001
                return {"error": f"Could not evaluate expression: {exc}"}
        if name == "current_time":
            return {"utc_time": dt.datetime.now(dt.timezone.utc).isoformat()}
        return {"error": f"Unknown tool '{name}'"}
