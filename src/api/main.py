"""Main entry point for the FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.endpoints import router
from src.config import settings

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

from src.retrieval.chain import RAGChain

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events."""
    logger.info("Starting up Intelligent Assistant API...")
    
    # Eagerly initialize the RAG Chain
    # This prevents the first user from waiting ~10s for model loading
    logger.info("Pre-loading RAG Chain (Embeddings & LLM)...")
    try:
        app.state.rag_chain = RAGChain()
        logger.info("RAG Chain loaded successfully.")
    except Exception as e:
        logger.error(f"Critical error loading RAG Chain: {e}")
        # We might want to raise here, but for now we'll log it
    
    yield
    
    logger.info("Shutting down...")
    app.state.rag_chain = None

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Intelligent Cultural Assistant",
        description="RAG-based API for recommending cultural events in Île-de-France.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # For POC, allow all. Restrict in production.
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(router, prefix="/api/v1")

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
