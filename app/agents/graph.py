from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import AgentState
from app.agents.nodes.planner import planner_node
from app.agents.nodes.retriever import retrieve_node
from app.agents.nodes.responder import generate_node
from app.agents.nodes.web_search import web_search_node

# 1. Initialize the State Graph
workflow = StateGraph(AgentState)


# 2. Define the Nodes
workflow.add_node("planner", planner_node)
workflow.add_node("retriever", retrieve_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("responder", generate_node)

# 3. Define the Edges & Routing Logic
def route_planner(state: AgentState):
    return state["route"]

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

checkpointer = MemorySaver()
rag_agent = workflow.compile(checkpointer=checkpointer)

