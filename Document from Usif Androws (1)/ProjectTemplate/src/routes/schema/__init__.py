
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChunkReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    chunk_id: str
    source: str
    score: float
    excerpt: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    include_context: bool = True
    source_filter: list[str] = Field(default_factory=list)


class QueryResponse(BaseModel):
    status: str = "ok"
    query: str
    answer: str
    generation_mode: str
    model: str
    retrieved_count: int
    retrieved_chunks: list[ChunkReference] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    collection: str | None = None


class IngestRequest(BaseModel):
    force_rebuild: bool = False
    paths: list[str] = Field(default_factory=list)
    extensions: list[str] = Field(default_factory=list)


class IngestResponse(BaseModel):
    status: str = "ok"
    documents_processed: int
    chunks_created: int
    indexed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    warnings: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    documents_directory: str
    documents_ready: bool
    documents_count: int
    chunks_count: int
    services: dict[str, str] = Field(default_factory=dict)# TIP: Initialize package exports here.
