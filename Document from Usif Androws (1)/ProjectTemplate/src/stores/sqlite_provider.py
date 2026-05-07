import sqlite3
import json
from typing import Sequence
from pathlib import Path

from src.helpers.config import Settings
from src.models import CorpusDocument, DocumentChunk
from src.models.db_schemes import ChunkRecord, DocumentRecord, IngestionRunRecord, QueryLogRecord
from src.stores.mongodb.provider import MetadataRepository

class SqliteMetadataRepository(MetadataRepository):
    provider_name = "sqlite"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db_path = settings.sqlite_db_path
        self._ensure_tables()

    def _get_connection(self):
        # Create directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    source TEXT PRIMARY KEY,
                    file_type TEXT,
                    checksum TEXT,
                    size_bytes INTEGER,
                    chunk_count INTEGER,
                    last_indexed_at TEXT,
                    metadata JSON
                )
            """)
            
            # chunks table 
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    source TEXT,
                    file_type TEXT,
                    position INTEGER,
                    page INTEGER,
                    text_preview TEXT,
                    metadata JSON
                )
            """)
            
            # ingestion_runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ingestion_runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT,
                    finished_at TEXT,
                    status TEXT,
                    documents_processed INTEGER,
                    chunks_created INTEGER,
                    warnings JSON
                )
            """)
            
            # queries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS queries (
                    query_id TEXT PRIMARY KEY,
                    created_at TEXT,
                    query TEXT,
                    requested_top_k INTEGER,
                    retrieved_count INTEGER,
                    latency_ms REAL,
                    metadata JSON
                )
            """)
            conn.commit()

    async def record_ingestion_run(self, run_record: IngestionRunRecord) -> None:
        data = run_record.model_dump(mode="json")
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ingestion_runs 
                (run_id, started_at, finished_at, status, documents_processed, chunks_created, warnings)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("run_id"), data.get("started_at"), data.get("finished_at"), data.get("status"),
                data.get("documents_processed"), data.get("chunks_created"), json.dumps(data.get("warnings", []))
            ))

    async def upsert_documents(self, documents: Sequence[CorpusDocument]) -> None:
        with self._get_connection() as conn:
            for document in documents:
                record = DocumentRecord(
                    source=document.source,
                    file_type=document.file_type,
                    checksum=document.checksum,
                    size_bytes=document.size_bytes,
                    chunk_count=document.chunk_count,
                    last_indexed_at=document.indexed_at,
                    metadata=document.metadata,
                )
                data = record.model_dump(mode="json")
                conn.execute("""
                    INSERT OR REPLACE INTO documents 
                    (source, file_type, checksum, size_bytes, chunk_count, last_indexed_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["source"], data["file_type"], data["checksum"], 
                    data["size_bytes"], data["chunk_count"], data["last_indexed_at"], 
                    json.dumps(data["metadata"]) if data["metadata"] else None
                ))

    async def upsert_chunks(self, chunks: Sequence[DocumentChunk]) -> None:
        with self._get_connection() as conn:
            for chunk in chunks:
                record = ChunkRecord(
                    chunk_id=chunk.chunk_id,
                    source=chunk.source,
                    file_type=chunk.file_type,
                    position=chunk.position,
                    page=chunk.page,
                    text_preview=chunk.text[:280],
                    metadata=chunk.metadata,
                )
                data = record.model_dump(mode="json")
                conn.execute("""
                    INSERT OR REPLACE INTO chunks 
                    (chunk_id, source, file_type, position, page, text_preview, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    data["chunk_id"], data["source"], data["file_type"], 
                    data["position"], data["page"], data["text_preview"], 
                    json.dumps(data["metadata"]) if data["metadata"] else None
                ))

    async def record_query(self, query_log: QueryLogRecord) -> None:
        data = query_log.model_dump(mode="json")
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO queries 
                (query_id, created_at, query, requested_top_k, retrieved_count, latency_ms, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("query_id"), data.get("created_at"), data.get("query"),
                data.get("requested_top_k"), data.get("retrieved_count"),
                data.get("latency_ms"), json.dumps(data.get("metadata", {}))
            ))
