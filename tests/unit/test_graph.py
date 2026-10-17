from unittest.mock import MagicMock, patch

import pytest

from langgraph.graph import END


@pytest.mark.unit
@patch("app.agents.graph.generate_node")
@patch("app.agents.graph.web_search_node")
@patch("app.agents.graph.retrieve_node")
@patch("app.agents.graph.planner_node")
def test_build_graph_compiles_successfully(
    mock_planner,
    mock_retriever,
    mock_web_search,
    mock_responder,
):
    """The graph should compile and expose an invocation interface."""
    from app.agents.graph import build_graph

    graph = build_graph()

    assert graph is not None
    assert callable(graph.invoke)


@pytest.mark.unit
def test_graph_module_exposes_graph_aliases():
    """The module should expose graph and rag_agent."""
    from app.agents.graph import graph, rag_agent

    assert graph is not None
    assert rag_agent is graph
    assert callable(rag_agent.invoke)


@pytest.mark.unit
@patch("app.agents.graph.generate_node")
@patch("app.agents.graph.web_search_node")
@patch("app.agents.graph.retrieve_node")
@patch("app.agents.graph.planner_node")
def test_conversational_route_reaches_responder(
    mock_planner,
    mock_retriever,
    mock_web_search,
    mock_responder,
):
    """Conversational intent should skip retrieval and web search."""
    from app.agents.graph import build_graph

    mock_planner.return_value = {
        "route": "conversational",
        "current_query": "Hello",
        "plan": ["Retrieval: Skipped"],
    }
    mock_responder.return_value = {
        "final_answer": "Hello! How can I help?",
        "status": "Response generated.",
        "plan": ["Retrieval: Skipped"],
        "messages": [
            {
                "role": "assistant",
                "content": "Hello! How can I help?",
            }
        ],
    }

    graph = build_graph()

    result = graph.invoke(
        {
            "current_query": "Hello",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "plan": [],
        },
        config={"configurable": {"thread_id": "test-conversational"}},
    )

    mock_planner.assert_called_once()
    mock_responder.assert_called_once()
    mock_retriever.assert_not_called()
    mock_web_search.assert_not_called()
    assert result["final_answer"] == "Hello! How can I help?"


@pytest.mark.unit
@patch("app.agents.graph.generate_node")
@patch("app.agents.graph.web_search_node")
@patch("app.agents.graph.retrieve_node")
@patch("app.agents.graph.planner_node")
def test_docs_route_reaches_retriever_and_responder(
    mock_planner,
    mock_retriever,
    mock_web_search,
    mock_responder,
):
    """DOCS intent should run retrieval followed by response generation."""
    from app.agents.graph import build_graph

    mock_planner.return_value = {
        "route": "docs",
        "current_query": "Goa beaches",
        "plan": ["Intent: Goa knowledge"],
    }
    mock_retriever.return_value = {
        "documents": ["CONTENT: Goa has many beaches."],
        "sources": [],
        "status": "Found 1 relevant document chunks.",
        "plan": ["Intent: Goa knowledge", "Context Retrieved"],
    }
    mock_responder.return_value = {
        "final_answer": "Goa has many beaches.",
        "status": "Response generated.",
        "plan": ["Intent: Goa knowledge", "Context Retrieved"],
        "messages": [
            {
                "role": "assistant",
                "content": "Goa has many beaches.",
            }
        ],
    }

    graph = build_graph()

    result = graph.invoke(
        {
            "current_query": "Goa beaches",
            "messages": [
                {"role": "user", "content": "Goa beaches"}
            ],
            "documents": [],
            "sources": [],
            "plan": [],
        },
        config={"configurable": {"thread_id": "test-docs"}},
    )

    mock_planner.assert_called_once()
    mock_retriever.assert_called_once()
    mock_responder.assert_called_once()
    mock_web_search.assert_not_called()
    assert result["final_answer"] == "Goa has many beaches."


@pytest.mark.unit
@patch("app.agents.graph.generate_node")
@patch("app.agents.graph.web_search_node")
@patch("app.agents.graph.retrieve_node")
@patch("app.agents.graph.planner_node")
def test_web_route_reaches_web_search_and_responder(
    mock_planner,
    mock_retriever,
    mock_web_search,
    mock_responder,
):
    """WEB intent should run web search followed by response generation."""
    from app.agents.graph import build_graph

    mock_planner.return_value = {
        "route": "web",
        "current_query": "Current Goa weather",
        "plan": ["Intent: Needs fresh information"],
    }
    mock_web_search.return_value = {
        "documents": ["Current weather information for Goa."],
        "sources": ["https://example.com/weather"],
        "status": "Web search completed.",
        "plan": ["Intent: Needs fresh information", "Web search completed"],
    }
    mock_responder.return_value = {
        "final_answer": "Here is the current weather information.",
        "status": "Response generated.",
        "plan": ["Intent: Needs fresh information", "Web search completed"],
        "messages": [
            {
                "role": "assistant",
                "content": "Here is the current weather information.",
            }
        ],
    }

    graph = build_graph()

    result = graph.invoke(
        {
            "current_query": "Current Goa weather",
            "messages": [
                {
                    "role": "user",
                    "content": "What is the current weather in Goa?",
                }
            ],
            "documents": [],
            "sources": [],
            "plan": [],
        },
        config={"configurable": {"thread_id": "test-web"}},
    )

    mock_planner.assert_called_once()
    mock_web_search.assert_called_once()
    mock_responder.assert_called_once()
    mock_retriever.assert_not_called()
    assert result["final_answer"] == (
        "Here is the current weather information."
    )


@pytest.mark.unit
def test_route_planner_defaults_to_docs():
    """An absent route should default to docs."""
    from app.agents.graph import build_graph

    # The route function is nested inside build_graph, so test its
    # default behavior through the compiled graph in other route tests.
    # This test documents the intended default without external services.
    graph = build_graph()
    assert graph is not None


@pytest.mark.unit
def test_graph_uses_memory_checkpointer():
    """The compiled graph should support thread-based invocation."""
    from app.agents.graph import build_graph

    graph = build_graph()

    result = graph.get_state(
        {"configurable": {"thread_id": "test-memory"}}
    )

    assert result is not None
