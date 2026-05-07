
from abc import ABC, abstractmethod
from typing import Sequence

from pymongo import MongoClient

from src.helpers.config import Settings
from src.models import CorpusDocument, DocumentChunk
from src.models.db_schemes import ChunkRecord, DocumentRecord, IngestionRunRecord, QueryLogRecord


class MetadataRepository(ABC):
    provider_name: str = "metadata"

    @abstractmethod
    async def record_ingestion_run(self, run_record: IngestionRunRecord) -> None:
        raise NotImplementedError

    @abstractmethod
    async def upsert_documents(self, documents: Sequence[CorpusDocument]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def upsert_chunks(self, chunks: Sequence[DocumentChunk]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def record_query(self, query_log: QueryLogRecord) -> None:
        raise NotImplementedError


class NoopMetadataRepository(MetadataRepository):
    provider_name = "noop"

    async def record_ingestion_run(self, run_record: IngestionRunRecord) -> None:
        return None

    async def upsert_documents(self, documents: Sequence[CorpusDocument]) -> None:
        return None

    async def upsert_chunks(self, chunks: Sequence[DocumentChunk]) -> None:
        return None

    async def record_query(self, query_log: QueryLogRecord) -> None:
        return None


class MongoMetadataRepository(MetadataRepository):
    provider_name = "mongo"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = MongoClient(settings.mongodb_url, serverSelectionTimeoutMS=2000)
        self._db = self._client[settings.mongodb_database]
        self._ready = False

    async def record_ingestion_run(self, run_record: IngestionRunRecord) -> None:
        self._ensure_indexes()
        self._db["ingestion_runs"].insert_one(run_record.model_dump(mode="json"))

    async def upsert_documents(self, documents: Sequence[CorpusDocument]) -> None:
        self._ensure_indexes()
        collection = self._db["documents"]
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
            collection.update_one(
                {"source": record.source},
                {"$set": record.model_dump(mode="json")},
                upsert=True,
            )

    async def upsert_chunks(self, chunks: Sequence[DocumentChunk]) -> None:
        self._ensure_indexes()
        collection = self._db["chunks"]
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
            collection.update_one(
                {"chunk_id": record.chunk_id},
                {"$set": record.model_dump(mode="json")},
                upsert=True,
            )

    async def record_query(self, query_log: QueryLogRecord) -> None:
        self._ensure_indexes()
        self._db["queries"].insert_one(query_log.model_dump(mode="json"))

    def _ensure_indexes(self) -> None:
        if self._ready:
            return

        self._db["documents"].create_index("source", unique=True)
        self._db["chunks"].create_index("chunk_id", unique=True)
        self._db["queries"].create_index("query_id", unique=True)
        self._db["ingestion_runs"].create_index("run_id", unique=True)
        self._ready = True


from src.stores.sqlite_provider import SqliteMetadataRepository

def create_metadata_repository(settings: Settings) -> MetadataRepository:
    if settings.metadata_store_provider.lower() == "mongo":
        return MongoMetadataRepository(settings)
    if settings.metadata_store_provider.lower() == "sqlite":
        return SqliteMetadataRepository(settings)
    return NoopMetadataRepository()
