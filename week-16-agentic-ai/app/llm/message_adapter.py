from __future__ import annotations

import json
from typing import Any, Dict, List


def to_openai_messages(canonical: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    openai_messages: List[Dict[str, Any]] = []
    for msg in canonical:
        role, content = msg["role"], msg["content"]

        if role == "system":
            openai_messages.append({"role": "system", "content": content})
            continue

        if isinstance(content, str):
            openai_messages.append({"role": role, "content": content})
            continue

        if role == "assistant":
            text_parts = [b["text"] for b in content if b.get("type") == "text"]
            tool_use_blocks = [b for b in content if b.get("type") == "tool_use"]
            entry: Dict[str, Any] = {"role": "assistant", "content": " ".join(text_parts) or None}
            if tool_use_blocks:
                entry["tool_calls"] = [
                    {
                        "id": b["id"],
                        "type": "function",
                        "function": {"name": b["name"], "arguments": json.dumps(b["input"])},
                    }
                    for b in tool_use_blocks
                ]
            openai_messages.append(entry)
            continue

        if role == "user":
            tool_results = [b for b in content if b.get("type") == "tool_result"]
            if tool_results:
                for b in tool_results:
                    openai_messages.append(
                        {"role": "tool", "tool_call_id": b["tool_use_id"], "content": b["content"]}
                    )
                continue
            text_parts = [b["text"] for b in content if b.get("type") == "text"]
            openai_messages.append({"role": "user", "content": " ".join(text_parts)})

    return openai_messages
