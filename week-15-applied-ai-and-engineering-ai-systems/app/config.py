from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM providers 
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-6", alias="ANTHROPIC_MODEL")

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")

    # Groq
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")

    local_llm_base_url: Optional[str] = Field(default=None, alias="LOCAL_LLM_BASE_URL")
    local_llm_model: str = Field(default="meta-llama/Meta-Llama-3-8B-Instruct", alias="LOCAL_LLM_MODEL")

    # Order in which providers are attempted. First one that's configured AND
    # succeeds wins; the rest form the fallback chain.
    provider_priority: List[str] = Field(default=["anthropic", "openai", "groq", "local"], alias="PROVIDER_PRIORITY")

    # Generation parameters 
    default_temperature: float = Field(default=0.4, alias="DEFAULT_TEMPERATURE")
    default_top_p: float = Field(default=0.9, alias="DEFAULT_TOP_P")
    max_tool_iterations: int = Field(default=5, alias="MAX_TOOL_ITERATIONS")
    max_output_tokens: int = Field(default=1024, alias="MAX_OUTPUT_TOKENS")

    # RAG 
    embedding_model_name: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")
    chroma_persist_dir: str = Field(default="./data/chroma", alias="CHROMA_PERSIST_DIR")
    chroma_collection: str = Field(default="knowledge_base", alias="CHROMA_COLLECTION")
    chunk_size: int = Field(default=800, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=120, alias="CHUNK_OVERLAP")
    retrieval_k: int = Field(default=4, alias="RETRIEVAL_K")

    # Reliability 
    redis_url: Optional[str] = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    cache_ttl_seconds: int = Field(default=3600, alias="CACHE_TTL_SECONDS")
    rate_limit_per_minute: int = Field(default=30, alias="RATE_LIMIT_PER_MINUTE")
    retry_max_attempts: int = Field(default=3, alias="RETRY_MAX_ATTEMPTS")
    circuit_breaker_cooldown_seconds: int = Field(default=60, alias="CIRCUIT_BREAKER_COOLDOWN_SECONDS")

    # App
    app_name: str = "AI Assistant"
    api_prefix: str = "/api/v1"
    cors_origins: List[str] = Field(default=["*"], alias="CORS_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
