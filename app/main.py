"""Main FastAPI application."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db, dispose_db
from app.api.routes import router as api_router

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(settings.app_debug and "DEBUG" or "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("🚀 Starting Stock News API...")
    logger.info(f"Debug mode: {settings.app_debug}")
    
    try:
        # Initialize database tables
        await init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

    try:
        yield
    finally:
        # Cleanup
        await dispose_db()
        logger.info("🛑 Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Stock News API",
    description="Stock news aggregation system with Finnhub, AlphaVantage, and GNews sources",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, tags=["API"])


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Stock News API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


@app.get("/docs", include_in_schema=False)
async def documentation():
    """Redirect to Swagger UI."""
    return {"message": Redirecting to /docs Swagger UI...}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
