
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.models import CorpusDocument
from src.routes.schema import HealthResponse, IngestRequest, IngestResponse, QueryRequest, QueryResponse

from pathlib import Path

# Set up templates - works in both local and Docker environments
# In Docker: /app/src/routes/__init__.py -> parents[2] = /app
# In local: /.../ProjectTemplate/src/routes/__init__.py -> need to find "templates"
def find_templates_dir():
    """Find the templates directory by searching parent directories"""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        templates_dir = parent / "templates"
        if templates_dir.exists():
            return templates_dir
    # Fallback: use /app/templates (Docker) or assume templates is at same level as src
    return Path("/app/templates")

templates = Jinja2Templates(directory=str(find_templates_dir()))


def get_controller(request: Request):
    controller = getattr(request.app.state, "controller", None)
    if controller is None:
        raise HTTPException(status_code=503, detail="RAG controller is not initialized")
    return controller


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api", tags=["rag"])

    @router.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        controller = get_controller(request)
        return await controller.health()

    @router.post("/ingest", response_model=IngestResponse)
    async def ingest(payload: IngestRequest, request: Request) -> IngestResponse:
        controller = get_controller(request)
        return await controller.ingest(payload)

    @router.post("/query", response_model=QueryResponse)
    async def query(payload: QueryRequest, request: Request) -> QueryResponse:
        controller = get_controller(request)
        return await controller.query(payload)

    @router.get("/corpus", response_model=list[CorpusDocument])
    async def corpus(request: Request) -> list[CorpusDocument]:
        controller = get_controller(request)
        return await controller.corpus()

    return router


def build_pages_router() -> APIRouter:
    """Router for HTML pages (frontend)"""
    router = APIRouter(tags=["pages"])

    @router.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    @router.get("/upload", response_class=HTMLResponse)
    async def upload_page(request: Request):
        return templates.TemplateResponse("upload.html", {"request": request})

    @router.post("/upload")
    async def upload_cv(request: Request, file: UploadFile = File(...)):
        """Upload a CV file and process it"""
        controller = get_controller(request)
        settings = request.app.state.settings

        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in settings.supported_extensions:
            extensions_str = ', '.join(settings.supported_extensions)
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported: {extensions_str}"
            )

        # Save file to uploads directory
        upload_path = settings.uploads_dir / file.filename
        try:
            content = await file.read()
            upload_path.write_bytes(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

        # Trigger ingestion for the uploaded file
        try:
            ingest_payload = IngestRequest(
                paths=[str(upload_path)],
                force_rebuild=False
            )
            result = await controller.ingest(ingest_payload)
            return RedirectResponse(url="/upload?success=true", status_code=303)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

    @router.get("/chat", response_class=HTMLResponse)
    async def chat_page(request: Request):
        return templates.TemplateResponse("chat.html", {"request": request})

    return router# TIP: Initialize package exports here.
