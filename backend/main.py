"""
CabinetSight FastAPI backend.
Serves the CV inspection pipeline and static frontend.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import router

app = FastAPI(
    title="CabinetSight API",
    description="Control-cabinet quality inspection using ORB/AKAZE feature matching, OCR, and color analysis",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

FRONTEND_DIR = Path(__file__).parent.parent
if (FRONTEND_DIR / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")
    app.mount("/src", StaticFiles(directory=str(FRONTEND_DIR / "src")), name="src")

    from fastapi.responses import FileResponse

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
