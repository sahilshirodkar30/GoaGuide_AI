from app.logger import log
from pinecone import Pinecone
from app.config import settings
from app.services.retrieval.embedding import embed_query


# Initialize Pinecone client
pc = Pinecone(api_key=settings.pinecone_api_key)

def get_index():
    return pc.Index(settings.pinecone_index_name)


def search_enterprise_knowledge(query: str, limit: int = 8):
    """
    Performs semantic similarity search in the enterprise
    knowledge base using Pinecone.

    Returns:
        List of dictionaries containing content, source, and score.
    """
    try:
        query_vector = embed_query(query)
        index = get_index()
        response = index.query(
            vector=query_vector,
            top_k=limit,
            include_metadata=True,
            include_values=False,
        )

        results = []

        for match in response.get("matches", []):
            metadata = match.get("metadata") or {}

            results.append({
                "content": metadata.get("text", ""),
                "source": metadata.get("source", "Unknown"),
                "score": match.get("score", 0.0),
            })

        return results

    except Exception:
        log.exception("Pinecone enterprise knowledge search failed")
        return []
