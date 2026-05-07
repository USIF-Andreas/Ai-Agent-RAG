
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    chunk_id: str
    source: str
    text: str
    position: int
    page: int | None = None
    file_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CorpusDocument(BaseModel):
    source: str
    file_type: str
    checksum: str
    size_bytes: int
    chunk_count: int
    indexed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchHit(BaseModel):
    rank: int
    chunk_id: str
    source: str
    score: float
    excerpt: str
    metadata: dict[str, Any] = Field(default_factory=dict)# TIP: Initialize package exports here.
