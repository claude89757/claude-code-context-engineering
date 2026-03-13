import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import SessionLocal, init_db
from .models import Version
from .routers import versions, test_runs, scenarios, reports, trends, patrol
from .services.scheduler import run_batch_patrol, start_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = start_scheduler()

    # Auto-fill to 5 versions in background (non-blocking)
    asyncio.create_task(_auto_fill_versions())

    yield
    scheduler.shutdown()


async def _auto_fill_versions():
    """Check version count and auto-trigger patrol if fewer than 5."""
    await asyncio.sleep(1)  # Let the server finish startup first
    db = SessionLocal()
    try:
        version_count = db.query(Version).count()
        if version_count >= 5:
            return
        need = 5 - version_count
        logger.info("Only %d versions in DB, auto-triggering %d more", version_count, need)

        from .services.version_checker import get_all_npm_versions

        all_versions = await asyncio.get_event_loop().run_in_executor(
            None, get_all_npm_versions
        )
        existing = {v.version for v in db.query(Version.version).all()}
        candidates = [v for v in all_versions if v not in existing]
        to_analyze = candidates[-need:] if len(candidates) >= need else candidates
        if to_analyze:
            await run_batch_patrol(to_analyze)
    except Exception:
        logger.exception("Failed to auto-trigger initial patrol")
    finally:
        db.close()


app = FastAPI(
    title="Context Engineering Observatory",
    description="Monitor and analyze Claude Code context engineering across versions",
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
    return {"status": "ok", "service": "context-engineering-observatory"}


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
