from typing import TypedDict, List, Annotated
import operator


class AgentState(TypedDict):
    # Using Annotated with operator.add ensures that messages 
    # are appended to the history rather than replaced.
    messages: Annotated[List[dict], operator.add]
    route: str                  # "conversational" | "docs" | "web"
    current_query: str
    documents: List[str]
    sources: List[str]          # URLs for citations
    plan: List[str]
    status: str
    final_answer: str
