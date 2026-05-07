
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import time

from src.controllers import RAGController
from src.helpers.config import get_settings
from src.routes import build_router, build_pages_router


def find_static_dir():
    """Find the static directory by searching parent directories"""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        static_dir = parent / "static"
        if static_dir.exists():
            return static_dir
    # Fallback
    return Path("/app/static")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.state.settings = settings
    app.state.controller = RAGController(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files - search for the static directory
    app.mount("/static", StaticFiles(directory=str(find_static_dir())), name="static")

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
              f"{request.method} {request.url.path} - "
              f"{response.status_code} ({process_time:.0f}ms)")
        return response

    # API routes
    app.include_router(build_router())

    # Page routes (frontend)
    app.include_router(build_pages_router())

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "message": settings.app_name,
            "status": "running",
            "health": f"{settings.api_prefix}/health",
            "docs": "/docs",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
