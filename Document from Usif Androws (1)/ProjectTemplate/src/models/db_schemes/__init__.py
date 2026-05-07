
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class IngestionRunRecord(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "pending"
    documents_processed: int = 0
    chunks_created: int = 0
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentRecord(BaseModel):
    source: str
    file_type: str
    checksum: str
    size_bytes: int
    chunk_count: int
    last_indexed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkRecord(BaseModel):
    chunk_id: str
    source: str
    file_type: str
    position: int
    page: int | None = None
    text_preview: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class QueryLogRecord(BaseModel):
    query_id: str
    query: str
    requested_top_k: int
    retrieved_count: int
    created_at: datetime
    latency_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)# TIP: Initialize package exports here.
