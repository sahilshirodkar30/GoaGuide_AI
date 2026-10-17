
from app.agents.state import AgentState
from app.gateway import get_langchain_llm
from app.logger import log

llm = get_langchain_llm(feature="planner")


def planner_node(state: AgentState):
    """Choose conversational, documentation, or web-search routing."""

    messages = state.get("messages", [])

    history = ""
    for msg in messages[:-1]:
        role = "User" if msg.get("role") == "user" else "Assistant"
        history += f"{role}: {msg.get('content', '')}\n"

    user_message = (
        messages[-1].get("content", "")
        if messages
        else state.get("current_query", "")
    )

    prompt = f"""
You are the Planner for a Goa travel guide assistant.
Analyze the conversation history and latest user message.

CONVERSATION HISTORY:
{history}

LATEST MESSAGE:
"{user_message}"

Choose exactly ONE route:
1. CONVERSATIONAL - greetings, thanks, or questions answerable using
   only the conversation history.
2. DOCS - stable Goa knowledge, destinations, culture, history,
   food, itineraries, and travel tips.
3. WEB - current weather, prices, opening hours, transport schedules,
   events, news, and other time-sensitive information.

Output exactly one of:
CONVERSATIONAL
DOCS: <refined search query>
WEB: <refined search query>
"""

    with log.span("Planner Decision"):
        decision = llm.invoke(prompt).content.strip()
        log.info(f"Intent identified: {decision}")

    upper = decision.upper()

    if upper.startswith("CONVERSATIONAL"):
        return {
            "route": "conversational",
            "current_query": user_message,
            "status": "Handling conversationally using conversation history.",
            "plan": [
                "Intent: Conversational/Memory",
                "Retrieval: Skipped",
            ],
        }

    if upper.startswith("WEB"):
        query = decision.split(":", 1)[-1].strip() or user_message
        return {
            "route": "web",
            "current_query": query,
            "status": f"Searching the web for: {query}",
            "plan": ["Intent: Needs fresh information", f"Tavily Query: {query}"],
        }

    query = decision.split(":", 1)[-1].strip() if ":" in decision else decision
    query = query or user_message

    return {
        "route": "docs",
        "current_query": query,
        "status": f"Searching Goa knowledge sources for: {query}",
        "plan": ["Intent: Goa knowledge", f"Search Term: {query}"],
    }
