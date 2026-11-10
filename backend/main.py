"""
AI Lead Generator — FastAPI backend entry point.

Run with:
    uvicorn main:app --host 127.0.0.1 --port 8765

The backend serves the Angular production build at / (SPA fallback)
and exposes API routes under /api.
"""

import sys
from pathlib import Path

# Ensure backend/ is on the path so imports like `config`, `services` work
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routes import dashboard, generation, leads, logs, settings, verification
from config.settings import BACKEND_HOST, BACKEND_PORT, FRONTEND_DIST_DIR, ensure_dirs
from utils.logging_config import setup_logging, logger

# ---------------------------------------------------------------------------
# Logging + data init
# ---------------------------------------------------------------------------
setup_logging()
ensure_dirs()

from services.csv_service import init_csv
init_csv()

logger.info("AI Lead Generator backend starting...")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AI Lead Generator API",
    description="Local-first AI Lead Generation Dashboard powered by ScrapeGraphAI and Gemini",
    version="1.0.0",
)

# CORS — restricted to local origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8765",
        "http://localhost:8765",
        "http://127.0.0.1:4200",  # Angular dev server
        "http://localhost:4200",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(settings.router)
app.include_router(generation.router)
app.include_router(leads.router)
app.include_router(dashboard.router)
app.include_router(logs.router)
app.include_router(verification.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ai-lead-generator", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Static file serving (Angular SPA)
# ---------------------------------------------------------------------------
# Determine the browser build directory (Angular 20 may output to dist/<name>/browser)
_browser_dir = FRONTEND_DIST_DIR
if not (_browser_dir / "index.html").exists():
    # Try common Angular output structures
    for candidate in [
        FRONTEND_DIST_DIR / "browser",
        FRONTEND_DIST_DIR / "ai-lead-generator" / "browser",
        FRONTEND_DIST_DIR / "ai-lead-generator",
    ]:
        if (candidate / "index.html").exists():
            _browser_dir = candidate
            break

_index_html = _browser_dir / "index.html"


@app.get("/")
def serve_index():
    """Serve the Angular app's index.html."""
    if _index_html.exists():
        return FileResponse(str(_index_html))
    return JSONResponse(
        status_code=200,
        content={
            "message": "Backend is running. Frontend is not built yet.",
            "instructions": "Run Setup.bat to build the frontend, or run 'ng serve' for development.",
        },
    )


# Mount static assets if the build exists
if _browser_dir.exists() and (_browser_dir / "index.html").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_browser_dir / "assets")) if (_browser_dir / "assets").exists() else _browser_dir,
        name="assets",
    )
    # Also serve other static files (JS, CSS, fonts) from the browser dir
    for subdir_name in ["media"]:
        subdir = _browser_dir / subdir_name
        if subdir.exists():
            app.mount(f"/{subdir_name}", StaticFiles(directory=str(subdir)), name=subdir_name)


@app.get("/{full_path:path}")
def spa_fallback(full_path: str, request: Request):
    """
    SPA fallback: return index.html for any path that doesn't match an
    API route or a static file.
    """
    # Don't intercept API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    # Try to serve a static file from the browser dir
    file_path = _browser_dir / full_path
    if file_path.is_file():
        return FileResponse(str(file_path))

    # Fall back to index.html for Angular routing
    if _index_html.exists():
        return FileResponse(str(_index_html))

    raise HTTPException(status_code=404, detail="Not found")


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    logger.info(f"Backend started on http://{BACKEND_HOST}:{BACKEND_PORT}")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Backend shutting down...")


# ---------------------------------------------------------------------------
# Entrypoint for direct `python main.py`
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=False,
        log_level="info",
    )
