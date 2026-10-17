
import pytest

from app.config import Settings, get_settings


@pytest.mark.unit
def test_default_llm_settings():
    config = Settings(_env_file=None)

    assert config.llm_provider == "deepseek"
    assert config.deepseek_base_url == "https://api.deepseek.com"
    assert config.deepseek_model == "deepseek-chat"
    assert config.groq_model == "openai/gpt-oss-120b"


@pytest.mark.unit
def test_default_pinecone_settings():
    config = Settings(_env_file=None)

    assert config.pinecone_index_name == "goaguide-ai"
    assert config.pinecone_namespace == "goa-v1"
    assert config.embedding_model == "llama-text-embed-v2"
    assert config.embedding_dim == 1024
    assert config.top_k_retrieve == 20
    assert config.top_n_rerank == 5


@pytest.mark.unit
def test_default_web_search_settings(monkeypatch):
    """Verify defaults independently of environment configuration."""
    monkeypatch.delenv("ENABLE_WEB_SEARCH", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    config = Settings(_env_file=None)

    assert config.enable_web_search is False
    assert config.tavily_api_key == ""
    assert config.web_fallback_score == 0.35
    assert config.web_max_results == 3



@pytest.mark.unit
def test_default_app_settings():
    config = Settings(_env_file=None)

    assert config.api_url == "http://localhost:8080"
    assert config.app_api_key == "change-me"
    assert config.admin_api_key == "change-me"


@pytest.mark.unit
def test_environment_variable_overrides(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("PINECONE_API_KEY", "test-pinecone-key")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

    config = Settings(_env_file=None)

    assert config.deepseek_api_key == "test-deepseek-key"
    assert config.pinecone_api_key == "test-pinecone-key"
    assert config.groq_api_key == "test-groq-key"


@pytest.mark.unit
def test_numeric_settings_have_correct_types():
    config = Settings(_env_file=None)

    assert isinstance(config.embedding_dim, int)
    assert isinstance(config.top_k_retrieve, int)
    assert isinstance(config.top_n_rerank, int)
    assert isinstance(config.web_fallback_score, float)
    assert isinstance(config.web_max_results, int)


@pytest.mark.unit
def test_get_settings_returns_cached_instance():
    get_settings.cache_clear()

    try:
        first = get_settings()
        second = get_settings()

        assert first is second
    finally:
        get_settings.cache_clear()
