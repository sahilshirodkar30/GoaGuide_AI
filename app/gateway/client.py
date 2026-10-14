from langchain_openai import ChatOpenAI
from openai import AsyncOpenAI, OpenAI
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders

from app.config import settings

# Routing (fallback / retry / cache) lives in a Portkey saved config, because
# inline configs are blocked on this workspace. We pass its slug (pc-...)
# via the `config` argument, which becomes the x-portkey-config header.


def _make_headers(feature: str = "rag") -> dict:
    """Build Portkey headers referencing the saved config by slug."""
    if not settings.PORTKEY_PRIMARY_CONFIG_ID:
        raise ValueError(
            "PORTKEY_PRIMARY_CONFIG_ID is not set in .env. "
            "Get the pc-... slug from the Portkey dashboard."
        )
    return createHeaders(
        api_key=settings.PORTKEY_API_KEY,
        config=settings.PORTKEY_PRIMARY_CONFIG_ID,  # was config_id (wrong)
        metadata={
            "feature": feature,
            "_user": "rag-system",
            "environment": "production",
        },
    )


portkey_client = OpenAI(
    api_key=settings.PORTKEY_API_KEY,
    base_url=PORTKEY_GATEWAY_URL,
    default_headers=_make_headers(),
)


def get_langchain_llm(feature: str = "rag") -> ChatOpenAI:
    """Portkey-backed ChatOpenAI for LangChain nodes."""
    return ChatOpenAI(
        api_key=settings.PORTKEY_API_KEY,
        base_url=PORTKEY_GATEWAY_URL,
        model=f"@{settings.GROQ_SLUG}/gpt-5-mini",
        default_headers=_make_headers(feature),
    )


def get_async_openai_client(feature: str = "rag") -> AsyncOpenAI:
    """Async OpenAI client routed through Portkey."""
    return AsyncOpenAI(
        api_key=settings.PORTKEY_API_KEY,
        base_url=PORTKEY_GATEWAY_URL,
        default_headers=_make_headers(feature),
    )


def extract_cache_status(raw_response) -> str:
    """
    Read x-portkey-cache-status from a raw response obtained via
    `client.chat.completions.with_raw_response.create(...)`.
    Returns 'MISS' if the header is absent.
    """
    headers = getattr(raw_response, "headers", None)
    if headers is not None:
        status = headers.get("x-portkey-cache-status", "")
        if status:
            return status.upper()
    return "MISS"