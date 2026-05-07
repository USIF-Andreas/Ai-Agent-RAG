
import hashlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from langchain.text_splitter import RecursiveCharacterTextSplitter

from src.helpers.config import Settings
from src.models import CorpusDocument, DocumentChunk, SearchHit
from src.models.db_schemes import IngestionRunRecord, QueryLogRecord
from src.routes.schema import ChunkReference, HealthResponse, IngestRequest, IngestResponse, QueryRequest, QueryResponse
from src.stores.mongodb.provider import MetadataRepository, create_metadata_repository
from src.stores.llm.provider import LLMProvider, create_llm_provider
from src.stores.vectordb.provider import VectorStoreProvider, create_vector_store_provider


_ARABIC_CHARS = re.compile(r"[\u0600-\u06FF]")
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\u0600-\u06FF]+")
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")
_SCRIPT_PATTERN = re.compile(r"<script.*?>.*?</script>", re.IGNORECASE | re.DOTALL)
_STYLE_PATTERN = re.compile(r"<style.*?>.*?</style>", re.IGNORECASE | re.DOTALL)


class RAGController:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.ensure_runtime_dirs()
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.settings.chunk_size,
            chunk_overlap=self.settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
        )
        self._documents: list[CorpusDocument] = []
        self._chunks: list[DocumentChunk] = []
        self._ingestion_runs: list[IngestionRunRecord] = []
        self._query_logs: list[QueryLogRecord] = []
        self._last_indexed_at: datetime | None = None
        self._vector_store: VectorStoreProvider = create_vector_store_provider(settings)
        self._llm: LLMProvider = create_llm_provider(settings)
        self._metadata_store: MetadataRepository = create_metadata_repository(settings)

    async def health(self) -> HealthResponse:
        services = {
            "vector_store": self._vector_store.provider_name,
            "llm": self._llm.provider_name,
            "metadata": self._metadata_store.provider_name,
            "normalization": "arabic-aware" if self.settings.enable_arabic_normalization else "basic",
        }
        return HealthResponse(
            status="ok",
            app_name=self.settings.app_name,
            version=self.settings.app_version,
            documents_directory=str(self.settings.documents_dir),
            documents_ready=self.settings.documents_dir.exists(),
            documents_count=len(self._documents),
            chunks_count=len(self._chunks),
            services=services,
        )

    async def ingest(self, payload: IngestRequest) -> IngestResponse:
        run_id = self._make_run_id("ingest")
        run_record = IngestionRunRecord(run_id=run_id, started_at=self._now())
        self._ingestion_runs.append(run_record)

        if payload.force_rebuild:
            self._documents = []
            self._chunks = []

        start = time.perf_counter()
        documents, chunks, warnings, source_paths = self._build_corpus(payload.paths, payload.extensions)

        self._documents = documents
        self._chunks = chunks
        self._last_indexed_at = self._now()
        await self._vector_store.rebuild(self._chunks)
        await self._metadata_store.record_ingestion_run(run_record)
        await self._metadata_store.upsert_documents(self._documents)
        await self._metadata_store.upsert_chunks(self._chunks)

        run_record.status = "completed"
        run_record.finished_at = self._now()
        run_record.documents_processed = len(documents)
        run_record.chunks_created = len(chunks)
        run_record.warnings = warnings
        run_record.metadata = {"elapsed_ms": int((time.perf_counter() - start) * 1000)}

        return IngestResponse(
            documents_processed=len(documents),
            chunks_created=len(chunks),
            warnings=warnings,
            sources=source_paths,
            indexed_at=self._last_indexed_at or self._now(),
        )

    async def query(self, payload: QueryRequest) -> QueryResponse:
        start = time.perf_counter()
        if not self._chunks:
            await self.ingest(IngestRequest())

        top_k = payload.top_k or self.settings.top_k
        ranked_hits = await self._vector_store.search(payload.query, top_k, payload.source_filter)
        answer = await self._llm.generate_answer(payload.query, ranked_hits, self.settings)

        query_log = QueryLogRecord(
            query_id=self._make_run_id("query"),
            query=payload.query,
            requested_top_k=top_k,
            retrieved_count=len(ranked_hits),
            created_at=self._now(),
            latency_ms=int((time.perf_counter() - start) * 1000),
            metadata={"generation_mode": "retrieval-baseline"},
        )
        self._query_logs.append(query_log)
        await self._metadata_store.record_query(query_log)

        return QueryResponse(
            query=payload.query,
            answer=answer,
            generation_mode=self._llm.provider_name,
            model=self.settings.llm_model,
            retrieved_count=len(ranked_hits),
            retrieved_chunks=[
                ChunkReference(
                    rank=hit.rank,
                    chunk_id=hit.chunk_id,
                    source=hit.source,
                    score=hit.score,
                    excerpt=hit.excerpt,
                    metadata=hit.metadata,
                )
                for hit in ranked_hits
            ],
            collection="faiss_index",
        )

    async def corpus(self) -> list[CorpusDocument]:
        if not self._documents and self._has_source_files():
            await self.ingest(IngestRequest())
        return list(self._documents)

    def _build_corpus(
        self,
        requested_paths: Sequence[str],
        requested_extensions: Sequence[str],
    ) -> tuple[list[CorpusDocument], list[DocumentChunk], list[str], list[str]]:
        warnings: list[str] = []
        documents: list[CorpusDocument] = []
        chunks: list[DocumentChunk] = []
        sources: list[str] = []

        files = self._resolve_source_files(requested_paths, requested_extensions)
        for path in files:
            try:
                raw_pages = self._extract_pages(path)
            except Exception as exc:
                warnings.append(f"{path.name}: {type(exc).__name__}: {exc}")
                continue

            if not raw_pages:
                warnings.append(f"{path.name}: no extractable text found")
                continue

            checksum = hashlib.sha1(path.read_bytes()).hexdigest()
            source_label = self._display_source(path)
            document_chunks: list[DocumentChunk] = []

            for page_number, page_text in raw_pages:
                cleaned_page = self._clean_text(page_text)
                if not cleaned_page:
                    continue

                for local_position, chunk_text in enumerate(self._splitter.split_text(cleaned_page)):
                    normalized_chunk = self._clean_text(chunk_text)
                    if not normalized_chunk:
                        continue

                    chunk_id = hashlib.sha1(
                        f"{source_label}:{page_number}:{local_position}:{normalized_chunk}".encode("utf-8")
                    ).hexdigest()[:24]
                    metadata = {
                        "checksum": checksum,
                        "size_bytes": path.stat().st_size,
                        "file_type": path.suffix.lower().lstrip("."),
                        "page": page_number,
                        "language": self._detect_language(normalized_chunk),
                        "indexed_at": self._now().isoformat(),
                    }
                    document_chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            source=source_label,
                            text=normalized_chunk,
                            position=len(document_chunks),
                            page=page_number,
                            file_type=path.suffix.lower().lstrip("."),
                            metadata=metadata,
                        )
                    )

            if not document_chunks:
                warnings.append(f"{path.name}: text extracted but no chunks were created")
                continue

            documents.append(
                CorpusDocument(
                    source=source_label,
                    file_type=path.suffix.lower().lstrip("."),
                    checksum=checksum,
                    size_bytes=path.stat().st_size,
                    chunk_count=len(document_chunks),
                    indexed_at=self._now(),
                    metadata={
                        "pages": len(raw_pages),
                        "language": self._detect_language(document_chunks[0].text),
                    },
                )
            )
            chunks.extend(document_chunks)
            sources.append(source_label)

        return documents, chunks, warnings, sources

    def _resolve_source_files(self, requested_paths: Sequence[str], requested_extensions: Sequence[str]) -> list[Path]:
        if requested_paths:
            candidates: list[Path] = []
            for raw_path in requested_paths:
                candidate = Path(raw_path)
                if not candidate.is_absolute():
                    candidate = self.settings.documents_dir / candidate
                if candidate.exists() and candidate.is_file():
                    candidates.append(candidate)
            files = candidates
        else:
            files = [path for path in self.settings.documents_dir.rglob("*") if path.is_file()]

        allowed_extensions = {
            extension.lower() if extension.startswith(".") else f".{extension.lower()}"
            for extension in (requested_extensions or self.settings.supported_extensions)
        }
        return sorted(
            {
                path.resolve()
                for path in files
                if path.suffix.lower() in allowed_extensions and not path.name.startswith(".")
            },
            key=lambda item: str(item).lower(),
        )

    def _extract_pages(self, path: Path) -> list[tuple[int | None, str]]:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md"}:
            content = path.read_text(encoding="utf-8", errors="ignore")
            return [(None, content)] if content.strip() else []

        if suffix in {".html", ".htm"}:
            content = path.read_text(encoding="utf-8", errors="ignore")
            content = _SCRIPT_PATTERN.sub(" ", content)
            content = _STYLE_PATTERN.sub(" ", content)
            content = _HTML_TAG_PATTERN.sub(" ", content)
            content = _WHITESPACE_PATTERN.sub(" ", content).strip()
            return [(None, content)] if content else []

        if suffix == ".pdf":
            pages: list[tuple[int | None, str]] = []
            try:
                import fitz

                with fitz.open(path) as document:
                    for page_number, page in enumerate(document, start=1):
                        text = (page.get_text("text") or "").strip()
                        if text:
                            pages.append((page_number, text))
                if pages:
                    return pages
            except Exception:
                pages = []

            from pypdf import PdfReader

            reader = PdfReader(str(path))
            for page_number, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append((page_number, text))
            return pages

        content = path.read_text(encoding="utf-8", errors="ignore")
        return [(None, content)] if content.strip() else []

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""

        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = _WHITESPACE_PATTERN.sub(" ", cleaned).strip()
        if self.settings.enable_arabic_normalization:
            cleaned = self._normalize_arabic(cleaned)
        return cleaned

    def _normalize_arabic(self, text: str) -> str:
        normalized = text
        normalized = re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]", "", normalized)
        normalized = normalized.replace("أ", "ا")
        normalized = normalized.replace("إ", "ا")
        normalized = normalized.replace("آ", "ا")
        normalized = normalized.replace("ى", "ي")
        normalized = normalized.replace("ة", "ه")
        normalized = normalized.replace("ؤ", "و")
        normalized = normalized.replace("ئ", "ي")
        return normalized

    def _tokenize(self, text: str) -> list[str]:
        normalized = self._clean_text_for_search(text)
        return _TOKEN_PATTERN.findall(normalized)

    def _clean_text_for_search(self, text: str) -> str:
        normalized = text.lower()
        if self.settings.enable_arabic_normalization:
            normalized = self._normalize_arabic(normalized)
        normalized = _WHITESPACE_PATTERN.sub(" ", normalized)
        return normalized

    def _detect_language(self, text: str) -> str:
        if _ARABIC_CHARS.search(text):
            return "ar"
        if re.search(r"[A-Za-z]", text):
            return "en"
        return self.settings.default_language

    def _normalize_source_name(self, source: str) -> str:
        return source.strip().lower()

    def _display_source(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.settings.documents_dir))
        except ValueError:
            return str(path)

    def _has_source_files(self) -> bool:
        return any(path.is_file() for path in self.settings.documents_dir.rglob("*"))

    def _truncate(self, value: str, length: int = 280) -> str:
        if len(value) <= length:
            return value
        return value[: length - 3].rstrip() + "..."

    def _make_run_id(self, prefix: str) -> str:
        payload = f"{prefix}:{time.time_ns()}:{len(self._documents)}:{len(self._chunks)}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)# TIP: Initialize package exports here.
