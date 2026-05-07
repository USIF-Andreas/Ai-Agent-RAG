from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "RAG CV Matcher"
    app_version: str = "0.1.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api"

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    documents_dir: Path = Field(default_factory=lambda: BASE_DIR / "documents")
    uploads_dir: Path = Field(default_factory=lambda: BASE_DIR / "uploads")
    temp_dir: Path = Field(default_factory=lambda: BASE_DIR / "tmp")

    faiss_index_path: Path = Field(default_factory=lambda: BASE_DIR / "documents" / "faiss_index")
    sqlite_db_path: Path = Field(default_factory=lambda: BASE_DIR / "documents" / "metadata.db")

    ollama_base_url: str = "http://ollama:11434"
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/owl-alpha"
    llm_model: str = "llama3:8b"
    embedding_model: str = "nomic-embed-text"
    llm_provider: str = "ollama"
    vector_store_provider: str = "faiss"
    metadata_store_provider: str = "sqlite"
    embedding_dimension: int = 768

    chunk_size: int = 500
    chunk_overlap: int = 100
    top_k: int = 3
    max_context_chunks: int = 5

    default_language: str = "auto"
    supported_extensions: list[str] = Field(
        default_factory=lambda: [".txt", ".md", ".html", ".htm", ".pdf"]
    )

    @field_validator("supported_extensions", mode="before")
    @classmethod
    def parse_supported_extensions(cls, value: Any) -> list[str]:
        """Parse supported_extensions from various formats"""
        if value is None:
            return [".txt", ".md", ".html", ".htm", ".pdf"]
        
        # If it's already a proper list with string items, return it
        if isinstance(value, list) and all(isinstance(i, str) for i in value):
            # Clean up items
            result = []
            for item in value:
                item = item.strip().strip("'\"")
                if item:
                    result.append(item if item.startswith(".") else f".{item}")
            return result or [".txt", ".md", ".html", ".htm", ".pdf"]
        
        # Handle string values (from .env file)
        if isinstance(value, str):
            # Try to parse as JSON first
            try:
                import json
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return cls.parse_supported_extensions(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
            
            # Handle Python repr format like "['.txt', '.md']"
            if value.strip().startswith("[") and value.strip().endswith("]"):
                inner = value.strip()[1:-1]
                # Extract items using regex
                import re
                items = re.findall(r"['\"]([^'\"]+)['\"]", inner)
                if items:
                    return cls.parse_supported_extensions(items)
                # Fallback: simple split
                items = [i.strip().strip("'\"") for i in inner.split(",")]
                return cls.parse_supported_extensions(items)
            
            # Simple comma-separated
            items = [i.strip().strip("'\"") for i in value.split(",") if i.strip()]
            return cls.parse_supported_extensions(items)
        
        return [".txt", ".md", ".html", ".htm", ".pdf"]
    enable_arabic_normalization: bool = True
    enable_factory_pattern: bool = True

    def ensure_runtime_dirs(self) -> None:
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_dirs()
    return settings
