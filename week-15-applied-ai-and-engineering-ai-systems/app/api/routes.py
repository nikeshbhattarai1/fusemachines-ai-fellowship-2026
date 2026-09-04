from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File

from app.config import Settings, get_settings
from app.dependencies import (
    get_llm_client,
    get_rate_limiter,
    get_response_cache,
    get_tool_executor,
    get_vector_store,
    get_embedding_model,
)
from app.llm.prompts import SYSTEM_PROMPT
from app.llm.tools import ALL_TOOLS
from app.rag.ingest import chunk_text, load_text
from app.reliability.cache import ResponseCache
from app.schemas import ChatRequest, ChatResponse, HealthResponse, IngestResponse, RetrievedSource

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)):
    providers = {
        "anthropic": bool(settings.anthropic_api_key),
        "openai": bool(settings.openai_api_key),
        "groq": bool(settings.groq_api_key),
        "local": bool(settings.local_llm_base_url),
    }
    return HealthResponse(status="ok", providers=providers)


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
    cache: ResponseCache = Depends(get_response_cache),
    limiter=Depends(get_rate_limiter),
    tool_executor=Depends(get_tool_executor),
):
    client_key = payload.session_id or (request.client.host if request.client else "anonymous")
    if not limiter.allow(client_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please slow down and try again shortly.")

    # Resolved manually (rather than via Depends) so a misconfiguration --
    # e.g. no API key set for any provider -- degrades gracefully into a
    # clean 503 instead of an unhandled 500 during dependency resolution.
    try:
        client = get_llm_client()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    temperature = payload.temperature if payload.temperature is not None else settings.default_temperature
    top_p = payload.top_p if payload.top_p is not None else settings.default_top_p

    cache_key = ResponseCache.make_key(
        {
            "message": payload.message,
            "history": [h.model_dump() for h in payload.history],
            "temperature": temperature,
            "top_p": top_p,
        }
    )
    cached = cache.get(cache_key)
    if cached is not None:
        return ChatResponse(**cached, cached=True)

    # Build the canonical (Anthropic-style) conversation 
    messages: List[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in payload.history:
        messages.append({"role": turn.role, "content": [{"type": "text", "text": turn.content}]})
    messages.append({"role": "user", "content": [{"type": "text", "text": payload.message}]})

    provider_used = "unknown"
    retrieved: List[RetrievedSource] = []
    final = None

    # Agentic tool-calling loop, capped at max_tool_iterations 
    for iteration in range(settings.max_tool_iterations):
        forced_final = iteration == settings.max_tool_iterations - 1
        tool_choice = "emit_answer" if forced_final else None

        try:
            response, provider_used = client.chat(
                messages=messages,
                tools=ALL_TOOLS,
                temperature=temperature,
                top_p=top_p,
                max_tokens=settings.max_output_tokens,
                tool_choice=tool_choice,
            )
        except RuntimeError as exc:
            # All providers failed / are in circuit-breaker cooldown: degrade
            # gracefully with a clear error instead of a raw 500.
            raise HTTPException(status_code=503, detail=f"Assistant is temporarily unavailable: {exc}") from exc

        assistant_blocks = []
        if response.text:
            assistant_blocks.append({"type": "text", "text": response.text})
        for tc in response.tool_calls:
            assistant_blocks.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.input})
        messages.append({"role": "assistant", "content": assistant_blocks})

        emit_call = next((tc for tc in response.tool_calls if tc.name == "emit_answer"), None)
        if emit_call:
            final = emit_call.input
            break

        if not response.tool_calls:
            # Model answered in plain text without using emit_answer -- still
            # treat it as a final answer rather than erroring out.
            final = {"answer": response.text, "sources": [], "used_tools": [], "confidence": 0.5}
            break

        tool_result_blocks = []
        for tc in response.tool_calls:
            result = tool_executor.execute(tc.name, tc.input)
            if tc.name == "rag_search":
                for r in result.get("results", []):
                    retrieved.append(RetrievedSource(**r))
            tool_result_blocks.append({"type": "tool_result", "tool_use_id": tc.id, "content": json.dumps(result)})
        messages.append({"role": "user", "content": tool_result_blocks})

    if final is None:
        raise HTTPException(status_code=502, detail="Assistant could not produce a final answer in time.")

    used_tools = sorted(
        {
            b["name"]
            for m in messages
            if m["role"] == "assistant"
            for b in m["content"]
            if b.get("type") == "tool_use" and b["name"] != "emit_answer"
        }
    )

    result = ChatResponse(
        answer=final.get("answer", ""),
        sources=final.get("sources") or sorted({r.source for r in retrieved}),
        used_tools=final.get("used_tools") or used_tools,
        confidence=float(final.get("confidence", 0.5)),
        provider_used=provider_used,
        cached=False,
        retrieved_context=retrieved,
    )
    cache.set(cache_key, result.model_dump(exclude={"cached"}))
    return result


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    vector_store=Depends(get_vector_store),
    embedding_model=Depends(get_embedding_model),
):
    tmp_path = Path("/tmp") / f"{uuid.uuid4()}_{file.filename}"
    tmp_path.write_bytes(await file.read())
    try:
        text = load_text(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise HTTPException(status_code=400, detail="No extractable text found in file.")

    embeddings = embedding_model.embed(chunks)
    doc_id = vector_store.add_documents(chunks, embeddings, source=file.filename)
    return IngestResponse(document_id=doc_id, filename=file.filename, chunks_indexed=len(chunks))
