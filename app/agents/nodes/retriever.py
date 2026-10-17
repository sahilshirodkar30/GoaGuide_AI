
from app.logger import log
from app.agents.state import AgentState
from app.services.retrieval.pinecone_service import search_enterprise_knowledge
from app.services.retrieval.ranking_service import rerank_documents


def retrieve_node(state: AgentState):
    """Retrieve and rerank documents for a Goa knowledge query."""

    query = state.get("current_query", "")

    with log.span("Knowledge Retrieval"):
        raw_results = search_enterprise_knowledge(query, limit=15)
        log.info(f"Retrieved {len(raw_results)} candidates from vector DB")

        doc_contents = [
            doc["content"]
            for doc in raw_results
            if doc.get("content")
        ]

        with log.span("Semantic Reranking"):
            reranked_contents = rerank_documents(
                query,
                doc_contents,
                top_n=5,
            )

        formatted_docs = [
            f"CONTENT: {doc}"
            for doc in reranked_contents
        ]

    return {
        "documents": formatted_docs,
        "sources": state.get("sources", []),
        "status": f"Found {len(formatted_docs)} relevant document chunks.",
        "plan": state.get("plan", []) + ["Context Retrieved"],
    }


# Backward compatibility for older callers and tests.
retriever_node = retrieve_node
