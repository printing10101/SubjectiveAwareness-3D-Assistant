import time
import asyncio
import httpx
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.database import engine, get_db, Base
from app.models.user import User
from app.utils.auth import auth_router, get_password_hash
from app.routers import (
    cases,
    analysis,
    documents,
    knowledge,
    reports,
    system,
    experiment,
)
from pipeline import analyze_pipeline

# Create tables
Base.metadata.create_all(bind=engine)

# Validate JWT security configuration
settings.validate_jwt_security()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Case Analysis API...")
    logger.info(
        f"Ollama URL: {settings.OLLAMA_BASE_URL}, Model: {settings.OLLAMA_MODEL}"
    )

    # Check Ollama availability
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if settings.OLLAMA_MODEL in model_names or any(
                    settings.OLLAMA_MODEL.split(":")[0] in m for m in model_names
                ):
                    logger.info(f"Model '{settings.OLLAMA_MODEL}' is available.")
                else:
                    logger.warning(
                        f"Model '{settings.OLLAMA_MODEL}' not found. "
                        f"Available: {model_names}"
                    )
            else:
                logger.warning(f"Ollama responded with status {response.status_code}")
    except Exception as e:
        logger.error(f"Ollama startup check failed: {e}")

    # Pre-cache demo cases
    logger.info("Pre-caching demo cases in background...")
    asyncio.create_task(pre_cache_demo_cases())

    # Create default admin user
    create_default_admin()

    yield

    # Shutdown
    logger.info("Shutting down Case Analysis API...")


async def pre_cache_demo_cases():
    """Pre-cache demo cases in background."""
    demo_cases = [
        "嫌疑人声称案发时在家睡觉，但监控显示其车辆出现在案发现场附近。",
    ]
    for case_text in demo_cases:
        try:
            await analyze_pipeline(case_text)
        except Exception as e:
            logger.error(f"Failed to pre-cache demo case: {e}")


# Initialize app
app = FastAPI(title="Case Analysis API", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=settings.cors_methods_list,
    allow_headers=settings.cors_headers_list,
)

# Include routers
app.include_router(analysis.router)
app.include_router(cases.router)
app.include_router(documents.router)
app.include_router(knowledge.router)
app.include_router(reports.router)
app.include_router(system.router)
app.include_router(experiment.router)
app.include_router(auth_router)


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)

    # Log content length if available
    content_length = request.headers.get("content-length", "N/A")
    response_time = int((time.time() - start_time) * 1000)

    logger.info(
        f"Request: {request.method} {request.url.path} | "
        f"Content-Length: {content_length} | "
        f"Response Time: {response_time}ms | "
        f"Status: {response.status_code}"
    )

    return response


@app.get("/health")
async def health_check():
    ollama_status = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                ollama_status = "available"
            else:
                ollama_status = "error"
    except Exception:
        ollama_status = "unavailable"

    return {
        "status": "healthy",
        "ollama": ollama_status,
        "model": settings.OLLAMA_MODEL,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Create default admin user on first run
def create_default_admin():
    db = next(get_db())
    try:
        existing = (
            db.query(User)
            .filter(User.username == settings.DEFAULT_ADMIN_USERNAME)
            .first()
        )
        if not existing:
            admin = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                role="admin",
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(admin)
            db.commit()
            logger.info(
                f"Created default admin user: {settings.DEFAULT_ADMIN_USERNAME}"
            )
    except Exception as e:
        logger.error(f"Failed to create default admin: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
    )
