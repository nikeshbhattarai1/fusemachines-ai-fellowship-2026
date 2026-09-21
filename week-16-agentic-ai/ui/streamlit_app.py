import html
import os
import uuid
from datetime import datetime

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://localhost:8000/api/v1")

st.set_page_config(page_title="AI Assistant",
                   page_icon="🔷", layout="wide")

# Theme
st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}

    .stApp {
        background: #0f1115;
    }

    /* Header bar */
    .console-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 18px 24px;
        background: linear-gradient(135deg, #1a1d24 0%, #14161c 100%);
        border: 1px solid #2a2d36;
        border-radius: 14px;
        margin-bottom: 18px;
    }
    .console-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #f2f3f5;
        letter-spacing: -0.5px;
        margin: 0;
    }
    .console-sub {
        color: #7d818c;
        font-size: 0.85rem;
        margin-top: 2px;
    }
    .pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        background: #1e2b23;
        color: #4ade80;
        border: 1px solid #2c4a38;
    }

    /* Chat bubbles */
    div[data-testid="stChatMessage"] {
        background: transparent;
        padding: 4px 0;
    }
    .bubble-user {
        background: #2563eb;
        color: white;
        padding: 12px 16px;
        border-radius: 16px 16px 4px 16px;
        max-width: 78%;
        margin-left: auto;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    .bubble-assistant {
        background: #1c1f26;
        border: 1px solid #2a2d36;
        color: #e5e6eb;
        padding: 12px 16px;
        border-radius: 16px 16px 16px 4px;
        max-width: 78%;
        font-size: 0.95rem;
        line-height: 1.5;
    }
    .meta-row {
        display: flex;
        gap: 8px;
        margin-top: 8px;
        flex-wrap: wrap;
    }
    .meta-chip {
        font-size: 0.7rem;
        padding: 3px 9px;
        border-radius: 999px;
        background: #23262e;
        color: #9298a3;
        border: 1px solid #2f333d;
    }
    .meta-chip.cached { color: #facc15; border-color: #4a3f1f; background: #201b0f; }
    .meta-chip.tool { color: #60a5fa; border-color: #223a5e; background: #101a2b; }

    /* Sidebar cards */
    section[data-testid="stSidebar"] {
        background: #14161c;
        border-right: 1px solid #23262e;
    }
    .side-card {
        background: #1a1d24;
        border: 1px solid #262932;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 14px;
    }
    .side-card h4 {
        color: #d1d3d8;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        margin: 0 0 10px 0;
    }

    div[data-testid="stChatInput"] {
        border-radius: 14px;
    }

    /* Verify mode */
    .status-chip { font-size: 0.75rem; font-weight: 600; padding: 3px 10px; border-radius: 999px; border: 1px solid; }
    .status-verified { color: #4ade80; background: #12261a; border-color: #2c4a38; }
    .status-partial, .status-budget_exhausted { color: #facc15; background: #201b0f; border-color: #4a3f1f; }
    .status-insufficient_evidence, .status-needs_clarification { color: #60a5fa; background: #101a2b; border-color: #223a5e; }
    .status-error { color: #f87171; background: #2a1414; border-color: #5a2626; }
    .claim {
        border: 1px solid #2a2d36; border-left-width: 4px; border-radius: 8px;
        padding: 9px 12px; margin: 8px 0; background: #171a20; color: #d7d9de; font-size: 0.88rem;
    }
    .claim.supported { border-left-color: #4ade80; }
    .claim.contradicted { border-left-color: #f87171; }
    .claim.conflicting { border-left-color: #facc15; }
    .claim.insufficient { border-left-color: #6b7280; }
    .verdict { font-weight: 600; margin-right: 8px; }
    .verdict.supported { color: #4ade80; } .verdict.contradicted { color: #f87171; }
    .verdict.conflicting { color: #facc15; } .verdict.insufficient { color: #9298a3; }
    .evidence-line { color: #9298a3; font-size: 0.8rem; margin-top: 4px; }
    .caveat {
        border: 1px solid #4a3f1f; background: #201b0f; color: #e8d9a0;
        border-radius: 8px; padding: 8px 12px; margin: 8px 0; font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "last_provider" not in st.session_state:
    st.session_state.last_provider = "—"

# Header
st.markdown(f"""
<div class="console-header">
    <div>
        <p class="console-title">◆ AI Assistant</p>
        <p class="console-sub">RAG · Tool calling · Anthropic → OpenAI → Groq → vLLM fallback</p>
    </div>
    <div style="text-align:right;">
        <span class="pill">● session {st.session_state.session_id}</span>
        <p class="console-sub" style="margin-top:6px;">last provider: {st.session_state.last_provider}</p>
    </div>
</div>
""", unsafe_allow_html=True)

VERDICT_TEXT = {"supported": "Supported", "contradicted": "Contradicted", "conflicting": "Sources conflict",
                "insufficient": "Not enough evidence"}
STATUS_TEXT = {"verified": "Verified", "partial": "Partly verified", "insufficient_evidence": "Not enough evidence",
               "needs_clarification": "Needs clarification", "budget_exhausted": "Stopped: budget used up", "error": "Error"}


def esc(text) -> str:
    """Model output and document text are untrusted: never inject them into HTML unescaped."""
    return html.escape(str(text)).replace("\n", "<br>")


def render_verify(data: dict) -> None:
    """One /verify response: answer, per-claim verdicts with quoted evidence, caveats, and the agent's trajectory."""
    st.markdown(f'<div class="bubble-assistant">{esc(data["answer"])}</div>', unsafe_allow_html=True)
    usage = data.get("usage", {})
    tokens = f'{usage.get("total_tokens", 0)}{" (est.)" if usage.get("estimated") else ""} tokens'
    chips = (f'<span class="status-chip status-{esc(data["status"])}">{esc(STATUS_TEXT.get(data["status"], data["status"]))}</span>'
             f'<span class="meta-chip">conf {data["confidence"]:.2f}</span>'
             f'<span class="meta-chip">{data["iterations"]} iteration(s)</span>'
             f'<span class="meta-chip">{esc(tokens)}</span>'
             f'<span class="meta-chip">{esc(data["provider_used"])}</span>')
    if data.get("degraded"):
        chips += '<span class="meta-chip cached">a source failed</span>'
    st.markdown(f'<div class="meta-row">{chips}</div>', unsafe_allow_html=True)

    for c in data.get("claims", []):
        v = c["verdict"]
        ev_lines = "".join(
            f'<div class="evidence-line">{esc(e["source"])} · “{esc(e["quote"])}”</div>' for e in c.get("evidence", []))
        badge = "" if not c.get("evidence") else (
            "cross-checked across sources" if c.get("corroborated") else "single source")
        st.markdown(
            f'<div class="claim {esc(v)}"><span class="verdict {esc(v)}">{esc(VERDICT_TEXT.get(v, v))}</span>'
            f'{esc(c["claim"])}{ev_lines}<div class="evidence-line">{esc(badge)}</div></div>', unsafe_allow_html=True)

    if data.get("limitations"):
        st.markdown('<div class="caveat"><b>Could not verify</b><br>' + "<br>".join(esc(x) for x in data["limitations"]) + "</div>",
                    unsafe_allow_html=True)

    with st.expander(f"How the agent got here ({data['iterations']} iteration(s), stopped: {data['stop_reason']})"):
        for step in data.get("trajectory", []):
            calls = step.get("calls", [])
            if not calls and step.get("error"):
                st.markdown(f"**Step {step['step']}** · error: `{str(step['error'])[:120]}`")
            for call in calls:
                args = ", ".join(f"{k}={str(v)[:50]!r}" for k, v in (call.get("args") or {}).items())
                outcome = call.get("summary") or ("; ".join(call.get("verifier_issues", [])) or ("ok" if call.get("ok") else "failed"))
                st.markdown(f"**Step {step['step']}** · `{call['tool']}({args.replace('`', chr(39))})` → {outcome.replace('`', chr(39))}")
    if data.get("evidence"):
        with st.expander(f"Evidence ledger ({len(data['evidence'])} passage(s))"):
            for e in data["evidence"]:
                st.markdown(f"`{e['id']}` **{e['source']}** — {e['text'].replace('`', chr(39))}")


# Sidebar
with st.sidebar:
    st.markdown('<div class="side-card"><h4>Knowledge Base</h4></div>',
                unsafe_allow_html=True)
    uploaded = st.file_uploader("Add a document", type=[
                                "txt", "md", "pdf"], label_visibility="collapsed")
    if uploaded and st.button("Ingest", use_container_width=True):
        with st.spinner("Chunking · embedding · indexing"):
            try:
                files = {"file": (uploaded.name, uploaded.getvalue())}
                resp = requests.post(
                    f"{API_URL}/ingest", files=files, timeout=120)
                if resp.ok:
                    data = resp.json()
                    st.success(
                        f"{data['chunks_indexed']} chunks indexed from {data['filename']}")
                else:
                    st.error(f"Ingestion failed: {resp.text}")
            except Exception as exc:
                st.error(f"Backend unreachable: {exc}")

    st.markdown('<div class="side-card"><h4>Mode</h4></div>', unsafe_allow_html=True)
    mode = st.radio("Mode", ["Chat", "Verify (agent)"], label_visibility="collapsed",
                    help="Verify runs the agent loop: it checks claims against several sources, searches again "
                         "when evidence is thin, and shows what it could not verify.")

    st.markdown('<div class="side-card"><h4>Generation</h4></div>',
                unsafe_allow_html=True)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.4, 0.05, disabled=mode != "Chat")
    top_p = st.slider("Top-p", 0.1, 1.0, 0.9, 0.05, disabled=mode != "Chat")

    st.markdown('<div class="side-card"><h4>System</h4></div>',
                unsafe_allow_html=True)
    if st.button("Ping backend", use_container_width=True):
        try:
            h = requests.get(f"{API_URL}/health", timeout=5).json()
            st.json(h)
        except Exception as exc:
            st.error(f"Backend unreachable: {exc}")

    if st.session_state.messages and st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Chat history
for msg in st.session_state.messages:
    role = msg["role"]
    with st.chat_message(role, avatar="🧑" if role == "user" else "🔷"):
        if msg.get("verify"):
            render_verify(msg["verify"])
            continue
        bubble_class = "bubble-user" if role == "user" else "bubble-assistant"
        st.markdown(
            f'<div class="{bubble_class}">{msg["content"]}</div>', unsafe_allow_html=True)

        meta = msg.get("meta")
        if meta:
            chips = f'<span class="meta-chip">{meta["provider_used"]}</span>'
            chips += f'<span class="meta-chip">conf {meta["confidence"]:.2f}</span>'
            if meta.get("cached"):
                chips += '<span class="meta-chip cached">⚡ cached</span>'
            for t in meta.get("used_tools", []):
                chips += f'<span class="meta-chip tool">🔧 {t}</span>'
            st.markdown(
                f'<div class="meta-row">{chips}</div>', unsafe_allow_html=True)
            if meta.get("sources"):
                with st.expander(f"{len(meta['sources'])} source(s)"):
                    for s in meta["sources"]:
                        st.markdown(f"- `{s}`")

# Input
if prompt := st.chat_input("Message the assistant..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(
            f'<div class="bubble-user">{prompt}</div>', unsafe_allow_html=True)

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages[:-1]
        if m["role"] in ("user", "assistant")
    ]

    with st.chat_message("assistant", avatar="🔷"):
        placeholder = st.empty()
        placeholder.markdown(
            '<div class="bubble-assistant">Thinking…</div>', unsafe_allow_html=True)
        if mode.startswith("Verify"):
            try:
                resp = requests.post(
                    f"{API_URL}/verify",
                    json={"session_id": st.session_state.session_id, "message": prompt, "history": history},
                    timeout=150,
                )
                if resp.status_code == 429:
                    raise RuntimeError("Rate limit reached. Wait a moment and try again.")
                resp.raise_for_status()
                data = resp.json()
                placeholder.empty()
                render_verify(data)
                st.session_state.last_provider = data["provider_used"]
                # `content` is what future turns see as history; for a clarification that is the question itself
                st.session_state.messages.append({"role": "assistant", "content": data["answer"], "verify": data})
            except Exception as exc:
                placeholder.markdown(
                    f'<div class="bubble-assistant">⚠️ Verification failed: {esc(exc)}</div>', unsafe_allow_html=True)
        else:
            try:
                resp = requests.post(
                    f"{API_URL}/chat",
                    json={
                        "session_id": st.session_state.session_id,
                        "message": prompt,
                        "history": history,
                        "temperature": temperature,
                        "top_p": top_p,
                    },
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()

                placeholder.markdown(
                    f'<div class="bubble-assistant">{data["answer"]}</div>', unsafe_allow_html=True)

                meta = {
                    "provider_used": data["provider_used"],
                    "confidence": data["confidence"],
                    "sources": data["sources"],
                    "used_tools": data["used_tools"],
                    "cached": data["cached"],
                }
                chips = f'<span class="meta-chip">{meta["provider_used"]}</span>'
                chips += f'<span class="meta-chip">conf {meta["confidence"]:.2f}</span>'
                if meta["cached"]:
                    chips += '<span class="meta-chip cached">⚡ cached</span>'
                for t in meta["used_tools"]:
                    chips += f'<span class="meta-chip tool">🔧 {t}</span>'
                st.markdown(
                    f'<div class="meta-row">{chips}</div>', unsafe_allow_html=True)

                st.session_state.last_provider = data["provider_used"]
                st.session_state.messages.append(
                    {"role": "assistant", "content": data["answer"], "meta": meta})
            except Exception as exc:
                placeholder.markdown(
                    f'<div class="bubble-assistant">⚠️ Request failed: {exc}</div>', unsafe_allow_html=True)
