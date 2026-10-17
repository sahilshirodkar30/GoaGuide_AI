from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with external services mocked."""
    with (
        patch("app.guardrails.initialize_rails"),
        patch("app.guardrails.guard", return_value=(False, None)),
    ):
        from app.main import app

        with TestClient(app) as test_client:
            yield test_client


@pytest.mark.unit
def test_home_endpoint(client):
    """The root endpoint should report that the API is live."""
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Enterprise LangGraph RAG API is live."
    }


@pytest.mark.unit
@patch("app.main.rag_agent")
def test_query_endpoint_returns_graph_answer(mock_agent, client):
    """A successful query should return the graph's answer and metadata."""
    mock_agent.invoke.return_value = {
        "final_answer": "Goa is known for its beaches.",
        "plan": ["Start", "Context Retrieved"],
        "status": "Response generated.",
        "documents": ["CONTENT: Goa has many beaches."],
    }

    response = client.post(
        "/query",
        json={
            "q": "Tell me about Goa",
            "thread_id": "test-thread",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["question"] == "Tell me about Goa"
    assert data["answer"] == "Goa is known for its beaches."
    assert data["thought_process"] == [
        "Start",
        "Context Retrieved",
    ]
    assert data["status"] == "Response generated."
    assert data["sources"] == [
        "CONTENT: Goa has many beaches."
    ]

    mock_agent.invoke.assert_called_once()

    args, kwargs = mock_agent.invoke.call_args
    initial_state = args[0]

    assert initial_state["current_query"] == "Tell me about Goa"
    assert initial_state["messages"] == [
        {"role": "user", "content": "Tell me about Goa"}
    ]
    assert kwargs["config"] == {
        "configurable": {"thread_id": "test-thread"}
    }


@pytest.mark.unit
@patch("app.main.guard", return_value=(
    True, "I can only help with Goa travel topics."
))
@patch("app.main.rag_agent")
def test_query_endpoint_returns_guardrail_response(
    mock_agent, mock_guard, client
):
    """A fired guardrail should return early without invoking the graph."""
    response = client.post(
        "/query",
        json={
            "q": "Tell me something unrelated",
            "thread_id": "guard-test",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["question"] == "Tell me something unrelated"
    assert data["answer"] == (
        "I can only help with Goa travel topics."
    )
    assert data["thought_process"] == [
        "Intent: Guardrails Fired",
        "Retrieval: Skipped",
    ]
    assert data["status"] == "Blocked by guardrails."
    assert data["sources"] == []

    mock_guard.assert_called_once_with(
        "Tell me something unrelated"
    )
    mock_agent.invoke.assert_not_called()


@pytest.mark.unit
@patch("app.main.guard", return_value=(False, None))
@patch("app.main.rag_agent")
def test_query_endpoint_handles_graph_exception(
    mock_agent, mock_guard, client
):
    """Graph errors should produce the API's fallback response."""
    mock_agent.invoke.side_effect = RuntimeError(
        "Simulated graph failure"
    )

    response = client.post(
        "/query",
        json={"q": "Goa travel"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["question"] == "Goa travel"
    assert data["answer"] == (
        "I apologize, but I encountered an internal error "
        "while processing your request. Please try again later."
    )
    assert data["thought_process"] == [
        "Error encountered during execution."
    ]
    assert data["status"] == "error"
    assert data["sources"] == []


@pytest.mark.unit
def test_query_endpoint_uses_default_thread_id(client):
    """An omitted thread_id should use default_user."""
    with patch(
        "app.main.rag_agent.invoke",
        return_value={
            "final_answer": "Welcome to Goa.",
            "plan": ["Start"],
            "status": "Response generated.",
            "documents": [],
        },
    ) as mock_invoke:
        response = client.post(
            "/query",
            json={"q": "Welcome"},
        )

    assert response.status_code == 200

    _, kwargs = mock_invoke.call_args

    assert kwargs["config"] == {
        "configurable": {"thread_id": "default_user"}
    }


@pytest.mark.unit
def test_query_endpoint_validates_missing_question(client):
    """The required q field must be supplied."""
    response = client.post(
        "/query",
        json={"thread_id": "missing-question"},
    )

    assert response.status_code == 422


@pytest.mark.unit
def test_query_endpoint_validates_empty_body(client):
    """An empty request body should fail validation."""
    response = client.post("/query", json={})

    assert response.status_code == 422


@pytest.mark.unit
@patch("app.main.rag_agent")
def test_graph_endpoint_returns_png(mock_agent, client):
    """The graph endpoint should return a PNG when rendering succeeds."""
    mock_graph = mock_agent.get_graph.return_value
    mock_graph.draw_mermaid_png.return_value = b"fake-png-content"

    response = client.get("/graph")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content == b"fake-png-content"


@pytest.mark.unit
@patch("app.main.rag_agent")
def test_graph_endpoint_handles_rendering_error(mock_agent, client):
    """A rendering failure should return an error object."""
    mock_agent.get_graph.side_effect = RuntimeError(
        "Rendering unavailable"
    )

    response = client.get("/graph")

    assert response.status_code == 200
    assert response.json() == {
        "error": "Could not generate graph image: Rendering unavailable"
    }
