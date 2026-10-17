from app.agents.state import AgentState
from app.gateway import get_langchain_llm
from app.logger import log

# Portkey-backed LLM: fallback + cache + retry — same .invoke() interface as ChatGroq
llm = get_langchain_llm(feature="planner")

def planner_node(state: AgentState):
    """
    The Planner determines if a search is needed based on the ENTIRE conversation.
    """
    # Get the conversation history (excluding the latest message)
    history = ""
    for msg in state["messages"][:-1]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history += f"{role}: {msg['content']}\n"
    
    user_message = state["messages"][-1]["content"] if state["messages"] else ""
    
    prompt = f"""
You are the Planner for a Goa travel guide assistant.
Analyze the conversation history and the latest user message.

CONVERSATION HISTORY:
{history}

LATEST MESSAGE:
"{user_message}"

Choose exactly ONE route:
1. CONVERSATIONAL - greetings, thanks, or questions answerable using ONLY the conversation history (e.g. "what is my name", "what did you suggest earlier").
2. DOCS - stable Goa knowledge in our guide: beaches, forts, churches, temples, food and dishes, culture, history, festivals (general), itineraries, neighborhoods, travel tips.
3. WEB - anything time-sensitive or changeable: today's weather, current events or dates, prices, opening hours, ferry/bus/train timings, new restaurants or clubs, news, safety alerts, flight info.

Output format (one line only):
CONVERSATIONAL
DOCS: <refined search query>
WEB: <refined search query>
"""
    
    with log.span("🧠 Planner Decision"):
        decision = llm.invoke(prompt).content.strip()
        log.info(f"Intent identified: {decision}")

    upper = decision.upper()
    
    if upper.startswith("CONVERSATIONAL"):
        return {
            "route": "conversational",
            "current_query": "",
            "status": "Handling conversationally (using memory)...",
            "plan": ["Intent: Conversational/Memory", "Retrieval: Skipped"],
        }

    if upper.startswith("WEB"):
        query = decision.split(":", 1)[-1].strip() or user_message
        return {
            "route": "web",
            "current_query": query,
            "status": f"Searching the web for: {query}",
            "plan": ["Intent: Needs fresh info", f"Tavily Query: {query}"],
        }
    
    query = decision.split(":", 1)[-1].strip() if ":" in decision else decision
    return {
        "route": "docs",
        "current_query": query or user_message,
        "status": f"Technical research needed. Searching docs for: {query}",
        "plan": ["Intent: Technical", f"Search Term: {query}"],
    }
