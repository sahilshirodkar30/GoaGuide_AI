from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    llm_provider: str = "deepseek"
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    groq_api_key: str = os.getenv("GROQ_API_KEY")
    groq_model: str = "openai/gpt-oss-120b"

    # Pinecone
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY")
    pinecone_index_name: str = "goaguide-ai"
    pinecone_namespace: str = "goa-v1"
    embedding_model: str = "llama-text-embed-v2"
    rerank_model: str = "bge-reranker-v2-m3"
    embedding_dim: int = 1024
    top_k_retrieve: int = 20
    top_n_rerank: int = 5
    pinecone_region : str= "us-east-1"

    # Observability
    LOGFIRE_TOKEN: str = os.getenv("LOGFIRE_TOKEN")
    logfire_environment: str = "development"

    # Web fallback
    enable_web_search: bool = False
    tavily_api_key: str = ""
    web_fallback_score: float = 0.35
    web_max_results: int = 3

    # App
    api_url: str = "http://localhost:8080"
    app_api_key: str = "change-me"
    admin_api_key: str = "change-me"

    # --- LLM GATEWAY (PORTKEY) ---
    PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")
    GROQ_SLUG =  "rag1"     # primary: @rag/llama-3.3-70b-versatile
    GROQ_SLUG_2 = "rag2"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()