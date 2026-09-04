from __future__ import annotations

import abc
import dataclasses
import json
import time
from typing import Any, Dict, List, Optional, Tuple

from app.config import Settings
from app.llm.message_adapter import to_openai_messages
from app.reliability.retry import PermanentProviderError, TransientProviderError, with_retry


@dataclasses.dataclass
class ToolCall:
    id: str
    name: str
    input: Dict[str, Any]


@dataclasses.dataclass
class ProviderResponse:
    stop_reason: str  # "tool_use" | "end_turn"
    text: str
    tool_calls: List[ToolCall]
    raw: Any = None


class LLMProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        temperature: float,
        top_p: float,
        max_tokens: int,
        tool_choice: Optional[str] = None,
    ) -> ProviderResponse:
        ...


def _to_openai_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        import anthropic  # local import: keeps this module importable without the SDK installed

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._sdk = anthropic

    @with_retry()
    def chat(self, messages, tools, temperature, top_p, max_tokens, tool_choice=None) -> ProviderResponse:
        system = next((m["content"] for m in messages if m["role"] == "system"), None)
        conv = [m for m in messages if m["role"] != "system"]
        tool_choice_param = {"type": "tool", "name": tool_choice} if tool_choice else {"type": "auto"}

        try:
            resp = self._client.messages.create(
                model=self._model,
                system=system,
                messages=conv,
                tools=tools,
                tool_choice=tool_choice_param,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
        except self._sdk.RateLimitError as exc:
            raise TransientProviderError(str(exc)) from exc
        except self._sdk.APIConnectionError as exc:
            raise TransientProviderError(str(exc)) from exc
        except self._sdk.APIStatusError as exc:
            if exc.status_code >= 500:
                raise TransientProviderError(str(exc)) from exc
            raise PermanentProviderError(str(exc)) from exc

        text_parts: List[str] = []
        tool_calls: List[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, input=block.input))

        return ProviderResponse(stop_reason=resp.stop_reason, text="".join(text_parts), tool_calls=tool_calls, raw=resp)


class OpenAICompatibleProvider(LLMProvider):
    """Works for hosted OpenAI *and* any OpenAI-compatible endpoint (e.g. a
    locally served vLLM instance) -- just point `base_url` at it."""

    def __init__(self, api_key: str, model: str, base_url: Optional[str] = None, name: str = "openai"):
        import openai  # local import: keeps this module importable without the SDK installed

        self._client = openai.OpenAI(api_key=api_key or "EMPTY", base_url=base_url)
        self._model = model
        self._sdk = openai
        self.name = name

    @with_retry()
    def chat(self, messages, tools, temperature, top_p, max_tokens, tool_choice=None) -> ProviderResponse:
        openai_messages = to_openai_messages(messages)
        tool_choice_param: Any = "auto"
        if tool_choice:
            tool_choice_param = {"type": "function", "function": {"name": tool_choice}}

        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                tools=_to_openai_tools(tools) if tools else None,
                tool_choice=tool_choice_param if tools else None,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
            )
        except self._sdk.RateLimitError as exc:
            raise TransientProviderError(str(exc)) from exc
        except self._sdk.APIConnectionError as exc:
            raise TransientProviderError(str(exc)) from exc
        except self._sdk.APIStatusError as exc:
            if exc.status_code >= 500:
                raise TransientProviderError(str(exc)) from exc
            raise PermanentProviderError(str(exc)) from exc

        choice = resp.choices[0]
        msg = choice.message
        tool_calls: List[ToolCall] = []
        for tc in msg.tool_calls or []:
            tool_calls.append(
                ToolCall(id=tc.id, name=tc.function.name, input=json.loads(tc.function.arguments or "{}"))
            )
        stop_reason = "tool_use" if tool_calls else "end_turn"
        return ProviderResponse(stop_reason=stop_reason, text=msg.content or "", tool_calls=tool_calls, raw=resp)


class CircuitBreaker:
    """Per-provider circuit breaker: after a failure, a provider is skipped for
    `cooldown_seconds` instead of being retried on every subsequent request."""

    def __init__(self, cooldown_seconds: int):
        self._cooldown = cooldown_seconds
        self._open_until: Dict[str, float] = {}

    def is_open(self, provider_name: str) -> bool:
        return time.monotonic() < self._open_until.get(provider_name, 0)

    def record_failure(self, provider_name: str) -> None:
        self._open_until[provider_name] = time.monotonic() + self._cooldown

    def record_success(self, provider_name: str) -> None:
        self._open_until.pop(provider_name, None)


class FallbackLLMClient:
    def __init__(self, providers: List[LLMProvider], breaker: CircuitBreaker):
        self._providers = providers
        self._breaker = breaker

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        temperature: float,
        top_p: float,
        max_tokens: int,
        tool_choice: Optional[str] = None,
    ) -> Tuple[ProviderResponse, str]:
        last_exc: Optional[Exception] = None
        for provider in self._providers:
            if self._breaker.is_open(provider.name):
                continue
            try:
                response = provider.chat(messages, tools, temperature, top_p, max_tokens, tool_choice)
                self._breaker.record_success(provider.name)
                return response, provider.name
            except Exception as exc:  # noqa: BLE001 - any provider failure triggers fallback
                self._breaker.record_failure(provider.name)
                last_exc = exc
                continue
        raise RuntimeError(f"All LLM providers failed or are in cooldown. Last error: {last_exc}")


def build_client(settings: Settings) -> FallbackLLMClient:
    providers: List[LLMProvider] = []
    for name in settings.provider_priority:
        if name == "anthropic" and settings.anthropic_api_key:
            providers.append(AnthropicProvider(settings.anthropic_api_key, settings.anthropic_model))
        elif name == "openai" and settings.openai_api_key:
            providers.append(OpenAICompatibleProvider(settings.openai_api_key, settings.openai_model, name="openai"))
        elif name == "groq" and settings.groq_api_key:
            # Groq exposes an OpenAI-compatible /v1/chat/completions endpoint,
            # including function calling, so it's just another base_url for
            # the same provider class -- no separate SDK needed.
            providers.append(
                OpenAICompatibleProvider(
                    api_key=settings.groq_api_key,
                    model=settings.groq_model,
                    base_url=settings.groq_base_url,
                    name="groq",
                )
            )
        elif name == "local" and settings.local_llm_base_url:
            providers.append(
                OpenAICompatibleProvider(
                    api_key="EMPTY",
                    model=settings.local_llm_model,
                    base_url=settings.local_llm_base_url,
                    name="local",
                )
            )
    if not providers:
        raise RuntimeError(
            "No LLM providers configured. Set ANTHROPIC_API_KEY, OPENAI_API_KEY, "
            "GROQ_API_KEY, or LOCAL_LLM_BASE_URL."
        )
    return FallbackLLMClient(providers, CircuitBreaker(settings.circuit_breaker_cooldown_seconds))
