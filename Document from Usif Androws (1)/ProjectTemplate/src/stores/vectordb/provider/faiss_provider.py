import hashlib
import math
import os
import re
import urllib.request
import urllib.error
from typing import Sequence
import numpy as np
import faiss
import json

from src.helpers.config import Settings
from src.models import DocumentChunk, SearchHit
from src.stores.vectordb.provider import VectorStoreProvider

class FaissVectorStoreProvider(VectorStoreProvider):
    provider_name = "faiss"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._index_path = str(settings.faiss_index_path)
        self._manifest_path = self._index_path + "_manifest.json"
        self._dimension = settings.embedding_dimension
        self._ollama_base_url = settings.ollama_base_url
        self._embedding_model = settings.embedding_model
        self._index = None
        self._chunks: dict[int, dict] = {}
        self._load_index()

    def _load_index(self):
        if os.path.exists(self._index_path) and os.path.exists(self._manifest_path):
            self._index = faiss.read_index(self._index_path)
            with open(self._manifest_path, "r", encoding="utf-8") as f:
                self._chunks = {int(k): v for k, v in json.load(f).items()}
        else:
            self._index = faiss.IndexFlatIP(self._dimension)
            self._chunks = {}

    def _save_index(self):
        os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
        faiss.write_index(self._index, self._index_path)
        with open(self._manifest_path, "w", encoding="utf-8") as f:
            json.dump(self._chunks, f)

    def _embed(self, text: str) -> list[float]:
        """Get embedding vector for text using Ollama API"""
        try:
            payload = json.dumps({
                "model": self._embedding_model,
                "prompt": text
            }).encode("utf-8")
            request = urllib.request.Request(
                f"{self._ollama_base_url}/api/embeddings",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
            embedding = body.get("embedding", [])
            if len(embedding) != self._dimension:
                # Pad or truncate to match expected dimension
                if len(embedding) < self._dimension:
                    embedding = embedding + [0.0] * (self._dimension - len(embedding))
                else:
                    embedding = embedding[:self._dimension]
            return embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return [0.0] * self._dimension

    async def rebuild(self, chunks: Sequence[DocumentChunk]) -> None:
        self._index = faiss.IndexFlatIP(self._dimension)
        self._chunks = {}
        if not chunks:
            self._save_index()
            return
            
        vectors = []
        for i, chunk in enumerate(chunks):
            vector = self._embed(chunk.text)
            vectors.append(vector)
            self._chunks[i] = {
                "chunk_id": chunk.chunk_id,
                "source": chunk.source,
                "file_type": chunk.file_type,
                "position": chunk.position,
                "page": chunk.page,
                "text": chunk.text,
                "language": chunk.metadata.get("language"),
                "metadata": chunk.metadata,
            }
            
        vectors_np = np.array(vectors, dtype=np.float32)
        self._index.add(vectors_np)
        self._save_index()

    async def search(
        self,
        query: str,
        top_k: int,
        source_filter: Sequence[str] | None = None,
    ) -> list[SearchHit]:
        if self._index is None or self._index.ntotal == 0:
            return []

        query_vector = np.array([self._embed(query)], dtype=np.float32)
        
        # Determine actual k considering filtering might remove results
        search_k = min(top_k * 5, self._index.ntotal)
        
        distances, indices = self._index.search(query_vector, search_k)
        
        normalized_filter = None
        if source_filter:
            normalized_filter = {self._normalize_source_name(item) for item in source_filter if item and item.strip()}

        hits: list[SearchHit] = []
        
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                break
                
            chunk_data = self._chunks.get(idx)
            if not chunk_data:
                continue
                
            text = chunk_data.get("text", "")
            source = str(chunk_data.get("source", "unknown"))
            
            if normalized_filter and self._normalize_source_name(source) not in normalized_filter:
                continue

            hits.append(
                SearchHit(
                    rank=0, # will set later
                    chunk_id=chunk_data["chunk_id"],
                    source=source,
                    score=round(float(dist), 4),
                    excerpt=self._make_excerpt(text, set(self._tokenize(query))),
                    metadata={
                        "file_type": chunk_data.get("file_type"),
                        "page": chunk_data.get("page"),
                        "language": chunk_data.get("language"),
                        "metadata": chunk_data.get("metadata", {}),
                    },
                )
            )
            
            if len(hits) >= top_k:
                break

        return [hit.model_copy(update={"rank": index + 1}) for index, hit in enumerate(hits)]


    def _make_excerpt(self, text: str, query_terms: set[str]) -> str:
        query_terms = set(query_terms)
        sentences = re.split(r"(?<=[.!?؟])\s+", text.strip())
        for sentence in sentences:
            if set(self._tokenize(sentence)) & query_terms:
                return self._truncate(sentence)
        return self._truncate(text)

    def _tokenize(self, text: str) -> list[str]:
        normalized = self._clean_text_for_search(text)
        from src.stores.vectordb.provider import _TOKEN_PATTERN
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
        from src.stores.vectordb.provider import _WHITESPACE_PATTERN
        return _WHITESPACE_PATTERN.sub(" ", normalized)

    def _normalize_source_name(self, source: str) -> str:
        return source.strip().lower()

    def _truncate(self, value: str, length: int = 280) -> str:
        if len(value) <= length:
            return value
        return value[: length - 3].rstrip() + "..."
