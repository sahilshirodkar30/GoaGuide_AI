from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.agents.nodes.responder import generate_node


def make_response(content="Test response"):
    """Create a mock Portkey completion response."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ]
    )


@pytest.mark.unit
@patch("app.agents.nodes.responder.extract_cache_status")
@patch("app.agents.nodes.responder.portkey_client")
def test_generate_node_returns_answer(
    mock_portkey, mock_cache_status
):
    """A successful LLM response should populate final_answer."""
    mock_portkey.chat.completions.create.return_value = (
        make_response("Goa is a popular travel destination.")
    )
    mock_cache_status.return_value = "MISS"

    state = {
        "current_query": "Tell me about Goa",
        "route": "docs",
        "documents": ["Goa is known for its beaches."],
        "messages": [
            {"role": "user", "content": "Tell me about Goa"}
        ],
        "plan": ["Intent: Goa knowledge"],
    }

    result = generate_node(state)

    assert result["final_answer"] == (
        "Goa is a popular travel destination."
    )
    assert result["status"] == "Response generated."
    assert result["plan"] == ["Intent: Goa knowledge"]
    assert result["messages"] == [
        {
            "role": "assistant",
            "content": "Goa is a popular travel destination.",
        }
    ]

    mock_portkey.chat.completions.create.assert_called_once()
    mock_cache_status.assert_called_once()


@pytest.mark.unit
@patch("app.agents.nodes.responder.extract_cache_status")
@patch("app.agents.nodes.responder.portkey_client")
def test_generate_node_handles_cache_hit(
    mock_portkey, mock_cache_status
):
    """A cache hit should update the plan and status."""
    mock_portkey.chat.completions.create.return_value = (
        make_response("Here is your answer.")
    )
    mock_cache_status.return_value = "HIT"

    state = {
        "current_query": "Goa beaches",
        "route": "docs",
        "documents": ["Goa has many beaches."],
        "messages": [
            {"role": "user", "content": "Goa beaches"}
        ],
        "plan": ["Context Retrieved"],
    }

    result = generate_node(state)

    assert result["final_answer"] == "Here is your answer."
    assert result["status"] == "Cache hit — instant response."
    assert result["plan"] == [
        "Context Retrieved",
        "Cache: Hit ⚡",
    ]


@pytest.mark.unit
@patch("app.agents.nodes.responder.extract_cache_status")
@patch("app.agents.nodes.responder.portkey_client")
def test_generate_node_conversational_route(
    mock_portkey, mock_cache_status
):
    """Conversational routes should use conversation history."""
    mock_portkey.chat.completions.create.return_value = (
        make_response("Hello! How can I help?")
    )
    mock_cache_status.return_value = "MISS"

    state = {
        "current_query": "Hello",
        "route": "conversational",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "plan": ["Retrieval: Skipped"],
    }

    result = generate_node(state)

    assert result["final_answer"] == "Hello! How can I help?"

    call_args = mock_portkey.chat.completions.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]

    assert "CONVERSATION HISTORY" in prompt
    assert '"Hello"' in prompt
    assert "TECHNICAL CONTEXT" not in prompt


@pytest.mark.unit
@patch("app.agents.nodes.responder.extract_cache_status")
@patch("app.agents.nodes.responder.portkey_client")
def test_generate_node_includes_documents_in_prompt(
    mock_portkey, mock_cache_status
):
    """Document context should be included in technical responses."""
    mock_portkey.chat.completions.create.return_value = (
        make_response("Baga Beach is in North Goa.")
    )
    mock_cache_status.return_value = "MISS"

    state = {
        "current_query": "Where is Baga Beach?",
        "route": "docs",
        "documents": [
            "CONTENT: Baga Beach is in North Goa."
        ],
        "messages": [
            {"role": "user", "content": "Where is Baga Beach?"}
        ],
        "plan": [],
    }

    generate_node(state)

    call_args = mock_portkey.chat.completions.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]

    assert "TECHNICAL CONTEXT" in prompt
    assert "Baga Beach is in North Goa." in prompt
    assert "Where is Baga Beach?" in prompt


@pytest.mark.unit
@patch("app.agents.nodes.responder.extract_cache_status")
@patch("app.agents.nodes.responder.portkey_client")
def test_generate_node_includes_conversation_history(
    mock_portkey, mock_cache_status
):
    """Previous user and assistant messages should appear in the prompt."""
    mock_portkey.chat.completions.create.return_value = (
        make_response("Three-day Goa itinerary.")
    )
    mock_cache_status.return_value = "MISS"

    state = {
        "current_query": "Suggest an itinerary",
        "route": "docs",
        "documents": ["Goa has beaches and heritage sites."],
        "messages": [
            {"role": "user", "content": "I am visiting Goa"},
            {
                "role": "assistant",
                "content": "How long will you stay?",
            },
            {
                "role": "user",
                "content": "Suggest an itinerary",
            },
        ],
        "plan": [],
    }

    generate_node(state)

    prompt = (
        mock_portkey.chat.completions.create
        .call_args.kwargs["messages"][0]["content"]
    )

    assert "User: I am visiting Goa" in prompt
    assert "Assistant: How long will you stay?" in prompt


@pytest.mark.unit
@patch("app.agents.nodes.responder.extract_cache_status")
@patch("app.agents.nodes.responder.portkey_client")
def test_generate_node_uses_expected_model_and_temperature(
    mock_portkey, mock_cache_status
):
    """The configured model alias and temperature should be passed."""
    mock_portkey.chat.completions.create.return_value = (
        make_response()
    )
    mock_cache_status.return_value = "MISS"

    state = {
        "current_query": "Goa travel",
        "route": "docs",
        "documents": ["Goa travel information."],
        "messages": [
            {"role": "user", "content": "Goa travel"}
        ],
        "plan": [],
    }

    generate_node(state)

    kwargs = (
        mock_portkey.chat.completions.create.call_args.kwargs
    )

    assert kwargs["model"].startswith("@")
    assert kwargs["temperature"] == 0.1
    assert kwargs["messages"][0]["role"] == "user"


@pytest.mark.unit
@patch("app.agents.nodes.responder.portkey_client")
def test_generate_node_reraises_portkey_error(mock_portkey):
    """Portkey errors should propagate to the caller."""
    mock_portkey.chat.completions.create.side_effect = (
        RuntimeError("Portkey request failed")
    )

    state = {
        "current_query": "Goa travel",
        "route": "docs",
        "documents": ["Goa travel information."],
        "messages": [
            {"role": "user", "content": "Goa travel"}
        ],
        "plan": [],
    }

    with pytest.raises(
        RuntimeError, match="Portkey request failed"
    ):
        generate_node(state)


@pytest.mark.unit
@patch("app.agents.nodes.responder.extract_cache_status")
@patch("app.agents.nodes.responder.portkey_client")
def test_generate_node_uses_query_when_messages_missing(
    mock_portkey, mock_cache_status
):
    """Without messages, the current query should be used."""
    mock_portkey.chat.completions.create.return_value = (
        make_response("Goa is a travel destination.")
    )
    mock_cache_status.return_value = "MISS"

    state = {
        "current_query": "Tell me about Goa",
        "route": "docs",
        "documents": ["Goa has beaches."],
        "plan": [],
    }

    result = generate_node(state)

    assert result["final_answer"] == (
        "Goa is a travel destination."
    )

    prompt = (
        mock_portkey.chat.completions.create
        .call_args.kwargs["messages"][0]["content"]
    )
    assert '"Tell me about Goa"' in prompt


@pytest.mark.unit
@patch("app.agents.nodes.responder.extract_cache_status")
@patch("app.agents.nodes.responder.portkey_client")
def test_generate_node_truncates_oversized_context(
    mock_portkey, mock_cache_status
):
    """Context exceeding the limit should be truncated."""
    mock_portkey.chat.completions.create.return_value = (
        make_response("Answer")
    )
    mock_cache_status.return_value = "MISS"

    first_doc = "A" * 15000
    second_doc = "B" * 15000

    state = {
        "current_query": "Explain the documents",
        "route": "docs",
        "documents": [first_doc, second_doc],
        "messages": [
            {
                "role": "user",
                "content": "Explain the documents",
            }
        ],
        "plan": [],
    }

    generate_node(state)

    prompt = (
        mock_portkey.chat.completions.create
        .call_args.kwargs["messages"][0]["content"]
    )

    assert first_doc in prompt
    assert second_doc not in prompt
