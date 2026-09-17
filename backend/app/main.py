import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.core.security import verify_admin_ip
from backend.app.services.cleanup_service import CleanupService
from backend.app.api.endpoints import router as api_router
from backend.app.api.auth import router as auth_router
from backend.app.api.admin import router as admin_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize DB and default admin
    init_db()
    # 2. Start background 3-day retention auto-cleanup worker
    cleanup_task = asyncio.create_task(CleanupService.start_retention_worker())
    yield
    # Shutdown
    cleanup_task.cancel()

docs_url = "/docs" if settings.ENVIRONMENT == "development" else None
redoc_url = "/redoc" if settings.ENVIRONMENT == "development" else None
openapi_url = "/openapi.json" if settings.ENVIRONMENT == "development" else None

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Short-form Reel & TikTok Subtitle Translation Studio (1GB VPS Optimized)",
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url
)

# 1. Security Headers Middleware (Clickjacking, MIME-sniffing, XSS defense)
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# 2. Hardened CORS Configuration
allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
if "*" in allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

# Register API routes (Isolated User vs Admin modules)
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(api_router, prefix="/api")

# Dedicated /admin route with IP restriction
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

@app.get("/admin")
async def serve_admin_portal(request: Request):
    """Guarded admin portal route. Rejects any non-whitelisted IP."""
    verify_admin_ip(request)
    index_file = frontend_dist / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h2>ReelCaption Admin Portal Ready (Build frontend to view UI)</h2>")

# Mount frontend production build if present
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {
            "app": settings.APP_NAME,
            "version": "1.0.0",
            "docs_url": "/docs",
            "health_url": "/api/health"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
