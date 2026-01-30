"""Main entry point for the FastAPI application."""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.api.endpoints import router
from src.config import settings
from src.data.ingestion import DataIngestionPipeline
from src.retrieval.chain import RAGChain
from src.utils.tracing import configure_trace_logging

# Configure logging with trace support
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
configure_trace_logging()
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Graceful shutdown handler
def setup_signal_handlers(app: FastAPI):
    """Setup signal handlers for graceful shutdown."""

    def shutdown_handler(signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}. Initiating graceful shutdown...")

        # Close RAG chain resources
        if hasattr(app.state, 'rag_chain') and app.state.rag_chain:
            try:
                logger.info("Closing RAG chain resources...")
                if hasattr(app.state.rag_chain, 'vector_store'):
                    app.state.rag_chain.vector_store.close()
                if hasattr(app.state.rag_chain, 'chat_storage'):
                    app.state.rag_chain.chat_storage.close()
                logger.info("RAG chain closed successfully")
            except Exception as e:
                logger.error(f"Error closing RAG chain: {e}")

        logger.info("Shutdown complete")
        sys.exit(0)

    # Register handlers for SIGTERM and SIGINT
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    logger.info("Signal handlers registered for graceful shutdown")

async def background_data_sync(app: FastAPI):
    """Background task to sync data every 12 hours."""
    # Wait a bit after startup before the first sync to not block resources
    await asyncio.sleep(60) 
    
    pipeline = DataIngestionPipeline()
    
    while True:
        try:
            logger.info("Starting scheduled background data sync...")
            stats = await pipeline.ingest()
            logger.info(f"Background sync complete: {stats.get('new_events_added', 0)} new events.")
            
            # If new events were added, reload the vector store in the active RAG chain
            if stats.get('new_events_added', 0) > 0 and hasattr(app.state, "rag_chain"):
                logger.info("New events found. Reloading FAISS index in RAGChain...")
                app.state.rag_chain.vector_store.load_index()
                
        except Exception as e:
            logger.error(f"Error during background data sync: {e}")
            
        # Wait 12 hours (12 * 60 * 60 seconds)
        logger.info("Next background sync in 12 hours.")
        await asyncio.sleep(12 * 3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events."""
    logger.info("Starting up Intelligent Assistant API...")
    
    # Eagerly initialize the RAG Chain
    logger.info("Pre-loading RAG Chain (Embeddings & LLM)...")
    try:
        app.state.rag_chain = RAGChain()
        logger.info("RAG Chain loaded successfully.")
    except Exception as e:
        logger.error(f"Critical error loading RAG Chain: {e}")
    
    # Start background sync task
    sync_task = asyncio.create_task(background_data_sync(app))
    
    yield
    
    logger.info("Shutting down...")
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass
    app.state.rag_chain = None

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Intelligent Cultural Assistant",
        description="RAG-based API for recommending cultural events in Île-de-France.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add rate limiter to app state
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

    # Setup graceful shutdown handlers
    setup_signal_handlers(app)

    logger.info("FastAPI app created with rate limiting (100 req/min per IP) and graceful shutdown")
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
