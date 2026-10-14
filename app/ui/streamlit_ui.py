import html
import os
import uuid

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

EXAMPLES = [
    "Plan a 3-day trip to North Goa",
    "Best beaches for a quiet sunset?",
    "Where can I try authentic Goan fish curry?",
    "What are the must-visit churches in Old Goa?",
]

WELCOME = (
    "**I'm your Goa guide.**\n\n"
    "Ask me about beaches, food, heritage sites, itineraries, or getting around. "
    "Pick a suggestion below or type your own question."
)
WORKFLOW = [
    "1. Receive your question",
    "2. Guardrails: block off-topic or unsafe requests",
    "3. Load conversation memory",
    "4. Planner: decide if Goa knowledge is needed",
    "5. Retriever: search the Goa knowledge base",
    "6. Skip search for simple questions",
    "7. Responder: write the answer from what was found",
    "8. Show the answer with its sources",
]
st.set_page_config(page_title="Goa Guide", page_icon="🌴", layout="wide")

# ---------- Styling ----------
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=DM+Sans:wght@400;500;700&display=swap');

:root{
  --sea:#0b2227; --sea-2:#10303a; --line:#1f4651;
  --shell:#eef4f0; --mist:#9bb7b8;
  --lagoon:#35c2b0; --laterite:#d2603a;
}
html, body, .stApp{font-family:'DM Sans',sans-serif}
.stApp{background:linear-gradient(180deg,#0b2227 0%,#081a1e 100%);color:var(--shell)}
[data-testid="stHeader"]{background:transparent}
[data-testid="stSidebar"]{background:#0a1d21;border-right:1px solid var(--line)}

h1.hero{font-family:'Fraunces',serif;font-weight:700;font-size:44px;line-height:1.05;
  margin:0 0 6px;color:var(--shell)}
.hero-sub{color:var(--mist);font-size:15px;margin-bottom:22px;max-width:60ch}

.side-title{font-family:'Fraunces',serif;font-size:30px;line-height:1.1;margin:6px 0 10px}
.muted{color:var(--mist);font-size:14px;line-height:1.55}

.status{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--mist);margin:14px 0}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.dot.on{background:var(--lagoon)} .dot.off{background:var(--laterite)}

div[data-testid="stChatMessage"]{background:var(--sea-2);border:1px solid var(--line);
  border-radius:14px}
.stButton>button{border:1px solid var(--line);background:var(--sea-2);color:var(--shell);
  border-radius:10px;text-align:left}
.stButton>button:hover{border-color:var(--lagoon);color:var(--lagoon)}
.stButton>button[kind="primary"]{background:var(--laterite);border-color:var(--laterite);color:#fff}

.trace-panel{border:1px solid var(--line);background:#0a1d21;border-radius:14px;padding:16px}
.trace-panel h3{font-family:'Fraunces',serif;margin:0 0 4px;font-size:20px}
.trace-item{font-size:13px;border-left:2px solid var(--lagoon);padding:6px 10px;margin:8px 0;
  color:var(--shell);background:var(--sea-2);border-radius:0 8px 8px 0}
.trace-item.warn{border-left-color:var(--laterite)}
.empty{color:var(--mist);font-size:13px}
.state-box{margin-top:16px;border-top:1px solid var(--line);padding-top:12px;font-size:13px;color:var(--mist)}
.state-box strong{color:var(--shell)}
.workflow-card{border:1px solid var(--line);background:var(--sea-2);padding:16px;border-radius:14px;margin:18px 0}
.workflow-card h3{margin:0 0 12px;font-size:14px}
.flow-step{font-size:13px;padding:8px 10px;border-left:2px solid var(--lagoon);color:var(--mist);margin:5px 0}
</style>
""",
    unsafe_allow_html=True,
)

# ---------- State ----------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME, "sources": []}]
if "trace" not in st.session_state:
    st.session_state.trace = []
if "status" not in st.session_state:
    st.session_state.status = "Idle"
if "pending" not in st.session_state:
    st.session_state.pending = None


# ---------- Backend helpers ----------
@st.cache_data(ttl=10, show_spinner=False)
def backend_online() -> bool:
    try:
        return requests.get(f"{BACKEND_URL}/", timeout=3).ok
    except requests.RequestException:
        return False


@st.cache_data(ttl=300, show_spinner=False)
def fetch_graph_png():
    try:
        r = requests.get(f"{BACKEND_URL}/graph", timeout=20)
        if r.ok and r.headers.get("content-type", "").startswith("image"):
            return r.content
    except requests.RequestException:
        pass
    return None


def source_to_text(src) -> str:
    """Backend 'documents' may be plain strings or dicts; normalise to text."""
    if isinstance(src, str):
        return src
    if isinstance(src, dict):
        for key in ("page_content", "content", "text"):
            if key in src:
                return str(src[key])
        return str(src)
    return str(src)


def ask_agent(question: str):
    st.session_state.messages.append({"role": "user", "content": question, "sources": []})
    payload = {"q": question, "thread_id": st.session_state.session_id}
    try:
        res = requests.post(f"{BACKEND_URL}/query", json=payload, timeout=90)
        res.raise_for_status()
        data = res.json()
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": data.get("answer") or "I couldn't find an answer to that.",
                "sources": [source_to_text(s) for s in (data.get("sources") or [])],
            }
        )
        st.session_state.trace = data.get("thought_process") or []
        st.session_state.status = data.get("status") or "Done"
    except requests.ConnectionError:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": f"I can't reach the backend at `{BACKEND_URL}`. Start the FastAPI server and try again.",
                "sources": [],
            }
        )
        st.session_state.trace = ["Backend unreachable"]
        st.session_state.status = "Offline"
    except Exception as e:
        st.session_state.messages.append(
            {"role": "assistant", "content": f"Something went wrong: {e}", "sources": []}
        )
        st.session_state.trace = ["Request failed"]
        st.session_state.status = "Error"


def reset_chat():
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = [{"role": "assistant", "content": WELCOME, "sources": []}]
    st.session_state.trace = []
    st.session_state.status = "Idle"


# ---------- Sidebar ----------
online = backend_online()
with st.sidebar:
    st.markdown(
        '<div class="side-title">Goa Guide</div>'
        '<p class="muted">Local knowledge, planned routes, and where to eat, '
        "answered by an agent that checks its sources.</p>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="status"><span class="dot {"on" if online else "off"}"></span>'
        f'Backend {"online" if online else "offline"}</div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Conversation ID: {st.session_state.session_id[:8]}")

    if st.button("New conversation", type="primary", width="stretch"):
        reset_chat()
        st.rerun()

    st.markdown(
        '<div class="workflow-card"><h3>LangGraph Workflow</h3>'
        + "".join(f'<div class="flow-step">{s}</div>' for s in WORKFLOW)
        + "</div>",
        unsafe_allow_html=True,
    )

# ---------- Handle input before rendering ----------
chat_prompt = st.chat_input("Ask about Goa...")
question = st.session_state.pending or chat_prompt
st.session_state.pending = None
if question:
    with st.spinner("Planning your answer..."):
        ask_agent(question.strip())

# ---------- Main layout ----------
main_col, trace_col = st.columns([3, 1], gap="large")

with main_col:
    st.markdown(
        '<h1 class="hero">Plan your Goa trip</h1>'
        '<div class="hero-sub">Beaches, food, heritage, and getting around, from North to South.</div>',
        unsafe_allow_html=True,
    )

    for msg in st.session_state.messages:
        avatar = "🌴" if msg["role"] == "assistant" else None
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander(f"Sources ({len(msg['sources'])})"):
                    for i, src in enumerate(msg["sources"], 1):
                        preview = src[:90].replace("\n", " ")
                        with st.expander(f"{i}. {preview}..."):
                            st.write(src)

    # Suggestions only while the chat is fresh
    if len(st.session_state.messages) == 1:
        cols = st.columns(2)
        for i, ex in enumerate(EXAMPLES):
            if cols[i % 2].button(ex, key=f"ex_{i}", width="stretch"):
                st.session_state.pending = ex
                st.rerun()

with trace_col:
    if st.session_state.trace:
        items = "".join(
            f'<div class="trace-item{" warn" if "guardrail" in str(t).lower() or "error" in str(t).lower() else ""}">'
            f"{html.escape(str(t))}</div>"
            for t in st.session_state.trace
        )
    else:
        items = '<div class="empty">Ask a question to see how the agent answers it.</div>'

    st.markdown(
        f"""
<div class="trace-panel">
<h3>Agent steps</h3>
<p class="muted">What the agent did for your last question.</p>
{items}
<div class="state-box">Status<br><strong>{html.escape(str(st.session_state.status))}</strong></div>
</div>""",
        unsafe_allow_html=True,
    )