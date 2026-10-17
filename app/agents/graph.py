
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.state import AgentState
from app.agents.nodes.planner import planner_node
from app.agents.nodes.retriever import retrieve_node
from app.agents.nodes.responder import generate_node
from app.agents.nodes.web_search import web_search_node


def build_graph():
    """Build and compile the GoaGuide AI agent graph."""
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("retriever", retrieve_node)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("responder", generate_node)

    def route_planner(state: AgentState):
        return state.get("route", "docs")

    workflow.set_entry_point("planner")

    workflow.add_conditional_edges(
        "planner",
        route_planner,
        {
            "conversational": "responder",
            "docs": "retriever",
            "web": "web_search",
        },
    )

    workflow.add_edge("retriever", "responder")
    workflow.add_edge("web_search", "responder")
    workflow.add_edge("responder", END)

    return workflow.compile(checkpointer=MemorySaver())


graph = build_graph()
rag_agent = graph
