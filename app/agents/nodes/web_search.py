# app/agents/nodes/web_search.py
import os
from tavily import TavilyClient
from app.agents.state import AgentState
from app.logger import log

tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def web_search_node(state: AgentState):
    query = state["current_query"]

    with log.span("🌐 Tavily Web Search"):
        try:
            response = tavily.search(
                query=query,
                search_depth="basic",     # "advanced" = better quality, 2x credits
                max_results=5,
                include_answer=False,
            )
            results = response.get("results", [])
        except Exception as e:
            log.error(f"Tavily search failed: {e}")
            results = []

        log.info(f"Tavily returned {len(results)} results")

    # Format into the same shape the responder already consumes (List[str])
    documents = [
        f"[Source: {r['title']} - {r['url']}]\n{r['content']}"
        for r in results
    ]
    sources = [r["url"] for r in results]

    return {
        "documents": documents,
        "sources": sources,
        "status": f"Found {len(results)} web results",
    }