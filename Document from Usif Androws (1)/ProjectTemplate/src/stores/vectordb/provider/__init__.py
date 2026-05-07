
import hashlib
import math
import re
import uuid
from abc import ABC, abstractmethod
from typing import Sequence

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from src.helpers.config import Settings
from src.models import DocumentChunk, SearchHit


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\u0600-\u06FF]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


class VectorStoreProvider(ABC):
    provider_name: str = "vector-store"

    @abstractmethod
    async def rebuild(self, chunks: Sequence[DocumentChunk]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int,
        source_filter: Sequence[str] | None = None,
    ) -> list[SearchHit]:
        raise NotImplementedError


class InMemoryVectorStoreProvider(VectorStoreProvider):
    provider_name = "memory"

    def __init__(self, enable_arabic_normalization: bool = True) -> None:
        self.enable_arabic_normalization = enable_arabic_normalization
        self._chunks: list[DocumentChunk] = []

    async def rebuild(self, chunks: Sequence[DocumentChunk]) -> None:
        self._chunks = list(chunks)

    async def search(
        self,
        query: str,
        top_k: int,
        source_filter: Sequence[str] | None = None,
    ) -> list[SearchHit]:
        normalized_filter = {
            self._normalize_source_name(item)
            for item in (source_filter or [])
            if item and item.strip()
        }
        query_terms = set(self._tokenize(query))
        if not query_terms:
            return []

        scored_hits: list[SearchHit] = []
        for chunk in self._chunks:
            if normalized_filter and self._normalize_source_name(chunk.source) not in normalized_filter:
                continue

            chunk_terms = set(self._tokenize(chunk.text))
            if not chunk_terms:
                continue

            shared_terms = query_terms & chunk_terms
            if not shared_terms:
                continue

            score = len(shared_terms) / math.sqrt(len(query_terms) * len(chunk_terms))
            scored_hits.append(
                SearchHit(
                    rank=0,
                    chunk_id=chunk.chunk_id,
                    source=chunk.source,
                    score=round(score, 4),
                    excerpt=self._make_excerpt(chunk.text, query_terms),
                    metadata=chunk.metadata,
                )
            )

        ranked_hits = sorted(scored_hits, key=lambda item: item.score, reverse=True)[:top_k]
        return [hit.model_copy(update={"rank": index + 1}) for index, hit in enumerate(ranked_hits)]

    def _make_excerpt(self, text: str, query_terms: set[str]) -> str:
        query_terms = set(query_terms)
        sentences = re.split(r"(?<=[.!?؟])\s+", text.strip())
        for sentence in sentences:
            if set(self._tokenize(sentence)) & query_terms:
                return self._truncate(sentence)
        return self._truncate(text)

    def _normalize_source_name(self, source: str) -> str:
        return source.strip().lower()

    def _tokenize(self, text: str) -> list[str]:
        normalized = self._clean_text_for_search(text)
        return _TOKEN_PATTERN.findall(normalized)

    def _clean_text_for_search(self, text: str) -> str:
        normalized = text.lower()
        if self.enable_arabic_normalization:
            normalized = self._normalize_arabic(normalized)
        return _WHITESPACE_PATTERN.sub(" ", normalized)

    def _normalize_arabic(self, text: str) -> str:
        normalized = re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]", "", text)
        normalized = normalized.replace("أ", "ا")
        normalized = normalized.replace("إ", "ا")
        normalized = normalized.replace("آ", "ا")
        normalized = normalized.replace("ى", "ي")
        normalized = normalized.replace("ة", "ه")
        normalized = normalized.replace("ؤ", "و")
        normalized = normalized.replace("ئ", "ي")
        return normalized

    def _truncate(self, value: str, length: int = 280) -> str:
        if len(value) <= length:
            return value
        return value[: length - 3].rstrip() + "..."


class QdrantVectorStoreProvider(VectorStoreProvider):
    provider_name = "qdrant"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
        self._collection_name = settings.qdrant_collection
        self._dimension = settings.embedding_dimension

    async def rebuild(self, chunks: Sequence[DocumentChunk]) -> None:
        try:
            await self._client.delete_collection(self._collection_name)
        except Exception:
            pass

        await self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=qmodels.VectorParams(
                size=self._dimension,
                distance=qmodels.Distance.COSINE,
            ),
        )

        if not chunks:
            return

        points: list[qmodels.PointStruct] = []
        for chunk in chunks:
            payload = {
                "chunk_id": chunk.chunk_id,
                "source": chunk.source,
                "file_type": chunk.file_type,
                "position": chunk.position,
                "page": chunk.page,
                "text": chunk.text,
                "language": chunk.metadata.get("language"),
                "metadata": chunk.metadata,
            }
            points.append(
                qmodels.PointStruct(
                    id=str(uuid.uuid5(uuid.NAMESPACE_URL, chunk.chunk_id)),
                    vector=self._embed(chunk.text),
                    payload=payload,
                )
            )

        await self._client.upsert(collection_name=self._collection_name, points=points)

    async def search(
        self,
        query: str,
        top_k: int,
        source_filter: Sequence[str] | None = None,
    ) -> list[SearchHit]:
        try:
            query_filter = self._build_filter(source_filter or [])
            results = await self._client.search(
                collection_name=self._collection_name,
                query_vector=self._embed(query),
                limit=top_k,
                query_filter=query_filter,
                with_payload=True,
            )
        except Exception:
            return []

        hits: list[SearchHit] = []
        for index, result in enumerate(results, start=1):
            payload = result.payload or {}
            text = str(payload.get("text", ""))
            hits.append(
                SearchHit(
                    rank=index,
                    chunk_id=str(result.id),
                    source=str(payload.get("source", "unknown")),
                    score=round(float(result.score or 0.0), 4),
                    excerpt=self._make_excerpt(text, self._tokenize(query)),
                    metadata={
                        "file_type": payload.get("file_type"),
                        "page": payload.get("page"),
                        "language": payload.get("language"),
                        "metadata": payload.get("metadata", {}),
                    },
                )
            )
        return hits

    def _build_filter(self, source_filter: Sequence[str]) -> qmodels.Filter | None:
        normalized_sources = [item.strip() for item in source_filter if item and item.strip()]
        if not normalized_sources:
            return None

        return qmodels.Filter(
            should=[
                qmodels.FieldCondition(
                    key="source",
                    match=qmodels.MatchValue(value=source),
                )
                for source in normalized_sources
            ],
            min_should=1,
        )

    def _make_excerpt(self, text: str, query_terms: set[str]) -> str:
        query_terms = set(query_terms)
        sentences = re.split(r"(?<=[.!?؟])\s+", text.strip())
        for sentence in sentences:
            if set(self._tokenize(sentence)) & query_terms:
                return self._truncate(sentence)
        return self._truncate(text)

    def _tokenize(self, text: str) -> list[str]:
        normalized = self._clean_text_for_search(text)
        return _TOKEN_PATTERN.findall(normalized)

    def _clean_text_for_search(self, text: str) -> str:
        normalized = text.lower()
        normalized = re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]", "", normalized)
        normalized = normalized.replace("أ", "ا")
        normalized = normalized.replace("إ", "ا")
        normalized = normalized.replace("آ", "ا")
        normalized = normalized.replace("ى", "ي")
        normalized = normalized.replace("ة", "ه")
        normalized = normalized.replace("ؤ", "و")
        normalized = normalized.replace("ئ", "ي")
        return _WHITESPACE_PATTERN.sub(" ", normalized)

    def _truncate(self, value: str, length: int = 280) -> str:
        if len(value) <= length:
            return value
        return value[: length - 3].rstrip() + "..."

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimension
        tokens = self._tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            index = int(hashlib.sha1(token.encode("utf-8")).hexdigest(), 16) % self._dimension
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return vector


from src.stores.vectordb.provider.faiss_provider import FaissVectorStoreProvider

def create_vector_store_provider(settings: Settings) -> VectorStoreProvider:
    if settings.vector_store_provider.lower() == "qdrant":
        return QdrantVectorStoreProvider(settings)
    if settings.vector_store_provider.lower() == "faiss":
        return FaissVectorStoreProvider(settings)
    return InMemoryVectorStoreProvider(enable_arabic_normalization=settings.enable_arabic_normalization)
