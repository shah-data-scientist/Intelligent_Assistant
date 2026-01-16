"""Main entry point for the FastAPI application."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.endpoints import router
from src.config import settings
from src.data.ingestion import DataIngestionPipeline
from src.retrieval.chain import RAGChain

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

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
