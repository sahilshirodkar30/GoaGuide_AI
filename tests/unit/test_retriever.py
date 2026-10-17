from unittest.mock import patch

import pytest

from app.agents.nodes.retriever import retrieve_node, retriever_node


@pytest.mark.unit
@patch("app.agents.nodes.retriever.rerank_documents")
@patch("app.agents.nodes.retriever.search_enterprise_knowledge")
def test_retrieve_node_returns_formatted_documents(
    mock_search, mock_rerank
):
    """Retrieved and reranked documents should be formatted as context."""
    mock_search.return_value = [
        {"content": "Baga Beach is in North Goa."},
        {"content": "Dudhsagar Falls is a popular attraction."},
    ]
    mock_rerank.return_value = [
        "Baga Beach is in North Goa."
    ]

    state = {
        "current_query": "Best places in Goa",
        "sources": ["guide.pdf"],
        "plan": ["Intent: Goa knowledge"],
    }

    result = retrieve_node(state)

    mock_search.assert_called_once_with(
        "Best places in Goa", limit=15
    )
    mock_rerank.assert_called_once_with(
        "Best places in Goa",
        [
            "Baga Beach is in North Goa.",
            "Dudhsagar Falls is a popular attraction.",
        ],
        top_n=5,
    )

    assert result["documents"] == [
        "CONTENT: Baga Beach is in North Goa."
    ]
    assert result["sources"] == ["guide.pdf"]
    assert result["status"] == (
        "Found 1 relevant document chunks."
    )
    assert result["plan"] == [
        "Intent: Goa knowledge",
        "Context Retrieved",
    ]


@pytest.mark.unit
@patch("app.agents.nodes.retriever.rerank_documents")
@patch("app.agents.nodes.retriever.search_enterprise_knowledge")
def test_retrieve_node_handles_no_search_results(
    mock_search, mock_rerank
):
    """No search results should produce an empty document list."""
    mock_search.return_value = []
    mock_rerank.return_value = []

    result = retrieve_node({"current_query": "Unknown topic"})

    mock_search.assert_called_once_with(
        "Unknown topic", limit=15
    )
    mock_rerank.assert_called_once_with(
        "Unknown topic", [], top_n=5
    )

    assert result["documents"] == []
    assert result["sources"] == []
    assert result["status"] == (
        "Found 0 relevant document chunks."
    )
    assert result["plan"] == ["Context Retrieved"]


@pytest.mark.unit
@patch("app.agents.nodes.retriever.rerank_documents")
@patch("app.agents.nodes.retriever.search_enterprise_knowledge")
def test_retrieve_node_filters_empty_content(
    mock_search, mock_rerank
):
    """Documents with missing or empty content should be filtered."""
    mock_search.return_value = [
        {"content": "Useful Goa travel information."},
        {"content": ""},
        {"metadata": {"source": "guide.pdf"}},
        {"content": None},
    ]
    mock_rerank.return_value = [
        "Useful Goa travel information."
    ]

    result = retrieve_node({
        "current_query": "Goa travel information"
    })

    mock_rerank.assert_called_once_with(
        "Goa travel information",
        ["Useful Goa travel information."],
        top_n=5,
    )
    assert result["documents"] == [
        "CONTENT: Useful Goa travel information."
    ]


@pytest.mark.unit
@patch("app.agents.nodes.retriever.rerank_documents")
@patch("app.agents.nodes.retriever.search_enterprise_knowledge")
def test_retrieve_node_preserves_sources_and_plan(
    mock_search, mock_rerank
):
    """Existing sources and planning steps should be preserved."""
    mock_search.return_value = [
        {"content": "Goa has Portuguese architectural heritage."}
    ]
    mock_rerank.return_value = [
        "Goa has Portuguese architectural heritage."
    ]

    state = {
        "current_query": "Goa heritage",
        "sources": ["heritage.pdf", "culture.md"],
        "plan": ["Intent: Goa knowledge", "Search completed"],
    }

    result = retrieve_node(state)

    assert result["sources"] == [
        "heritage.pdf",
        "culture.md",
    ]
    assert result["plan"] == [
        "Intent: Goa knowledge",
        "Search completed",
        "Context Retrieved",
    ]


@pytest.mark.unit
@patch("app.agents.nodes.retriever.rerank_documents")
@patch("app.agents.nodes.retriever.search_enterprise_knowledge")
def test_retrieve_node_uses_empty_query_when_missing(
    mock_search, mock_rerank
):
    """A missing current_query should default to an empty string."""
    mock_search.return_value = []
    mock_rerank.return_value = []

    result = retrieve_node({})

    mock_search.assert_called_once_with("", limit=15)
    mock_rerank.assert_called_once_with("", [], top_n=5)
    assert result["documents"] == []


@pytest.mark.unit
@patch("app.agents.nodes.retriever.rerank_documents")
@patch("app.agents.nodes.retriever.search_enterprise_knowledge")
def test_retriever_node_alias(
    mock_search, mock_rerank
):
    """The backward-compatible alias should call the same function."""
    mock_search.return_value = []
    mock_rerank.return_value = []

    result = retriever_node({"current_query": "Goa beaches"})

    assert result["documents"] == []
    mock_search.assert_called_once_with(
        "Goa beaches", limit=15
    )
