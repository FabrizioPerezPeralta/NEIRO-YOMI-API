import os
import sys

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, RedirectResponse
from .core.config import settings
from .core.database import Base, engine
from .api.v1.api import api_router
from .seed import seed_initial_data

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all models are registered on Base metadata
    from . import models
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    # Seed sample audiophile tracks, albums, artists, and demo user
    seed_initial_data()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Audiophile music streaming backend API for NEIRO YOMI. Hear Every Detail.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration (Production & Development support for third-party consumers)
cors_origins = settings.cors_origins_list
cors_kwargs = {
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
    "expose_headers": [
        "Content-Range",
        "Accept-Ranges",
        "Content-Length",
        "Content-Type",
        "Content-Disposition",
        "X-Audio-Bit-Depth",
        "X-Audio-Sample-Rate",
    ],
}

if "*" in cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://.*",
        **cors_kwargs,
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        **cors_kwargs,
    )

# Include API v1 Router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/app", tags=["Web App"])
def web_app():
    """Redirects to the Next.js / React Web Client on port 3000."""
    return RedirectResponse(url="http://localhost:3000", status_code=307)

@app.get("/", tags=["Root"])
@app.get("/api/info", tags=["Root"])
def api_info():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "slogan": "Hear Every Detail. The Art of Listening. 音を感じる。",
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
        "webApp": "http://localhost:3000"
    }

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "neiro-yomi-backend",
        "environment": "active"
    }

if __name__ == "__main__":
    import uvicorn
    target = "app.main:app" if os.path.exists("app/main.py") else "api.app.main:app"
    uvicorn.run(target, host="127.0.0.1", port=8000, reload=True)
