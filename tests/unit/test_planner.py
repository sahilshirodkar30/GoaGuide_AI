from unittest.mock import MagicMock, patch

import pytest

from app.agents.nodes.planner import planner_node


@pytest.mark.unit
@patch("app.agents.nodes.planner.llm")
def test_planner_routes_conversational_intent(mock_llm):
    """Greeting or conversational query should skip retrieval."""
    mock_llm.invoke.return_value = MagicMock(
        content="CONVERSATIONAL"
    )

    state = {
        "messages": [
            {"role": "user", "content": "Hello"}
        ]
    }

    result = planner_node(state)

    assert result["route"] == "conversational"
    assert result["current_query"] == "Hello"
    assert result["plan"] == [
        "Intent: Conversational/Memory",
        "Retrieval: Skipped",
    ]
    mock_llm.invoke.assert_called_once()


@pytest.mark.unit
@patch("app.agents.nodes.planner.llm")
def test_planner_routes_docs_intent(mock_llm):
    """Stable Goa knowledge should use document retrieval."""
    mock_llm.invoke.return_value = MagicMock(
        content="DOCS: Best beaches in North Goa"
    )

    state = {
        "messages": [
            {
                "role": "user",
                "content": "Tell me about Goa beaches",
            }
        ]
    }

    result = planner_node(state)

    assert result["route"] == "docs"
    assert result["current_query"] == "Best beaches in North Goa"
    assert "Best beaches in North Goa" in result["status"]
    assert result["plan"] == [
        "Intent: Goa knowledge",
        "Search Term: Best beaches in North Goa",
    ]


@pytest.mark.unit
@patch("app.agents.nodes.planner.llm")
def test_planner_routes_web_intent(mock_llm):
    """Current or time-sensitive information should use web search."""
    mock_llm.invoke.return_value = MagicMock(
        content="WEB: Current weather in Goa"
    )

    state = {
        "messages": [
            {
                "role": "user",
                "content": "What is the weather in Goa today?",
            }
        ]
    }

    result = planner_node(state)

    assert result["route"] == "web"
    assert result["current_query"] == "Current weather in Goa"
    assert "Current weather in Goa" in result["status"]
    assert result["plan"] == [
        "Intent: Needs fresh information",
        "Tavily Query: Current weather in Goa",
    ]


@pytest.mark.unit
@patch("app.agents.nodes.planner.llm")
def test_planner_uses_user_message_when_web_query_is_empty(mock_llm):
    """An empty WEB query should fall back to the latest user message."""
    mock_llm.invoke.return_value = MagicMock(
        content="WEB:"
    )

    user_message = "What is the weather in Goa today?"
    state = {
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }

    result = planner_node(state)

    assert result["route"] == "web"
    assert result["current_query"] == user_message


@pytest.mark.unit
@patch("app.agents.nodes.planner.llm")
def test_planner_uses_current_query_without_messages(mock_llm):
    """Missing messages should fall back to current_query."""
    mock_llm.invoke.return_value = MagicMock(
        content="CONVERSATIONAL"
    )

    state = {
        "messages": [],
        "current_query": "Tell me about Goa",
    }

    result = planner_node(state)

    assert result["route"] == "conversational"
    assert result["current_query"] == "Tell me about Goa"


@pytest.mark.unit
@patch("app.agents.nodes.planner.llm")
def test_planner_includes_conversation_history(mock_llm):
    """Previous messages should be included in the planner prompt."""
    mock_llm.invoke.return_value = MagicMock(
        content="DOCS: Goa itinerary"
    )

    state = {
        "messages": [
            {"role": "user", "content": "I am visiting Goa"},
            {
                "role": "assistant",
                "content": "How many days?",
            },
            {
                "role": "user",
                "content": "Suggest a three-day itinerary",
            },
        ]
    }

    planner_node(state)

    prompt = mock_llm.invoke.call_args.args[0]

    assert "User: I am visiting Goa" in prompt
    assert "Assistant: How many days?" in prompt
    assert "Suggest a three-day itinerary" in prompt


@pytest.mark.unit
@patch("app.agents.nodes.planner.llm")
def test_planner_defaults_to_docs_for_unrecognized_response(mock_llm):
    """Unrecognized planner output should default to document retrieval."""
    mock_llm.invoke.return_value = MagicMock(
        content="Some unexpected response"
    )

    state = {
        "messages": [
            {"role": "user", "content": "Tell me about Goa"}
        ]
    }

    result = planner_node(state)

    assert result["route"] == "docs"
    assert result["current_query"] == "Some unexpected response"


@pytest.mark.unit
@patch("app.agents.nodes.planner.llm")
def test_planner_handles_empty_docs_query(mock_llm):
    """An empty DOCS query should fall back to the user message."""
    mock_llm.invoke.return_value = MagicMock(
        content="DOCS:"
    )

    user_message = "Tell me about Goa's culture"
    state = {
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }

    result = planner_node(state)

    assert result["route"] == "docs"
    assert result["current_query"] == user_message
