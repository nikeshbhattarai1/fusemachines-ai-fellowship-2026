from __future__ import annotations

from typing import Any, Dict, List

from app.llm.tools import CALCULATOR_TOOL  # reused unchanged from W15

VERDICTS = ["supported", "contradicted", "conflicting", "insufficient"]

LIST_SOURCES_TOOL: Dict[str, Any] = {
    "name": "list_sources",
    "description": (
        "List the sources you can check claims against (documents and the structured facts registry) "
        "with their type, last-updated date and authority. Use it when you do not know what exists or how fresh it is."
    ),
    "input_schema": {"type": "object", "properties": {}},
}

KB_SEARCH_TOOL: Dict[str, Any] = {
    "name": "kb_search",
    "description": (
        "Semantic search over the document knowledge base. New passages are added to the evidence ledger "
        "(read their text there). Optionally restrict to one document with `source`."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to look for. Rephrase if a previous search missed."},
            "source": {"type": "string", "description": "Optional document name to restrict the search to."},
            "k": {"type": "integer", "description": "Max passages (default 4, max 6)."},
        },
        "required": ["query"],
    },
}

FACTS_LOOKUP_TOOL: Dict[str, Any] = {
    "name": "facts_lookup",
    "description": (
        "Look up an exact configuration value in the structured facts registry (authoritative for current "
        "settings). Provide an entity (e.g. 'rate limiter') and optionally an attribute."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "entity": {"type": "string", "description": "Component or topic, e.g. 'rate limiter', 'cache'."},
            "attribute": {"type": "string", "description": "Optional attribute, e.g. 'requests per minute'."},
        },
        "required": ["entity"],
    },
}

ASK_USER_TOOL: Dict[str, Any] = {
    "name": "ask_user",
    "description": (
        "Ask the user ONE clarifying question and stop. Use only when the request is ambiguous in a way that "
        "changes the answer and no source can resolve it."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "reason": {"type": "string", "description": "Why the ambiguity matters."},
        },
        "required": ["question"],
    },
}

FINISH_TOOL: Dict[str, Any] = {
    "name": "finish",
    "description": (
        "Deliver the final, verified answer. The application checks every cited evidence id and quote against the "
        "ledger and rejects unsupported claims."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string", "description": "Plain-language answer for the user."},
            "claims": {
                "type": "array",
                "description": "Each atomic claim you checked, with a verdict and its evidence.",
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string"},
                        "verdict": {"type": "string", "enum": VERDICTS},
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string", "description": "Ledger id, e.g. E3"},
                                    "quote": {"type": "string", "description": "Exact words copied from that evidence text."},
                                },
                                "required": ["id", "quote"],
                            },
                        },
                        "note": {"type": "string"},
                    },
                    "required": ["claim", "verdict"],
                },
            },
            "limitations": {"type": "array", "items": {"type": "string"}, "description": "What could not be verified and why."},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["answer", "claims", "confidence"],
    },
}

AGENT_TOOLS: List[Dict[str, Any]] = [
    LIST_SOURCES_TOOL, KB_SEARCH_TOOL, FACTS_LOOKUP_TOOL, CALCULATOR_TOOL, ASK_USER_TOOL, FINISH_TOOL,
]
TOOL_INDEX: Dict[str, Dict[str, Any]] = {t["name"]: t for t in AGENT_TOOLS}


def _check(value: Any, schema: Dict[str, Any], path: str, errors: List[str]) -> None:
    t = schema.get("type")
    if t == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string")
            return
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: must be one of {schema['enum']}")
    elif t == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            errors.append(f"{path}: expected integer")
    elif t == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errors.append(f"{path}: expected number")
    elif t == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array")
            return
        for i, item in enumerate(value):
            if "items" in schema:
                _check(item, schema["items"], f"{path}[{i}]", errors)
    elif t == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object")
            return
        for req in schema.get("required", []):
            if req not in value:
                errors.append(f"{path}.{req}: required")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                _check(value[key], sub, f"{path}.{key}", errors)


def validate_args(name: str, args: Any) -> List[str]:
    """Returns a list of human-readable problems (empty list == valid)."""
    if name not in TOOL_INDEX:
        return [f"unknown tool '{name}'"]
    errors: List[str] = []
    _check(args, TOOL_INDEX[name]["input_schema"], "args", errors)
    return errors
