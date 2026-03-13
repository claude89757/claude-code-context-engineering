from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import versions, test_runs, scenarios, reports, trends, patrol
from .services.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="CC Observatory",
    description="Claude Code Observatory - Monitor and analyze Claude Code updates",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(versions.router)
app.include_router(test_runs.router)
app.include_router(scenarios.router)
app.include_router(reports.router)
app.include_router(trends.router)
app.include_router(patrol.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "cc-observatory"}


# Serve frontend static files if the dist directory exists
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # Mount static assets (JS, CSS, etc.)
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    # SPA catch-all: serve index.html for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Try serving as a static file first
        file_path = frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for SPA routing
        return FileResponse(frontend_dist / "index.html")
