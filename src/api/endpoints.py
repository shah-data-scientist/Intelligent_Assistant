"""FastAPI endpoints for the Intelligent Assistant."""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from src.api.schemas import ChatRequest, ChatResponse
from src.retrieval.chain import RAGChain

logger = logging.getLogger(__name__)
router = APIRouter()

def get_rag_chain(request: Request) -> RAGChain:
    """Get the initialized RAGChain from app state."""
    chain = getattr(request.app.state, "rag_chain", None)
    if not chain:
        logger.error("RAGChain not initialized in app state.")
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    return chain

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "Intelligent Assistant API"}

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, chain: RAGChain = Depends(get_rag_chain)):
    """
    Process a user question about cultural events and return a response with sources.
    
    Executed synchronously in a thread pool to avoid blocking the asyncio event loop
    with heavy model inference calls.
    """
    try:
        logger.info(f"Received chat request: {request.question}")
        
        # Use query_with_metadata to get answer and sources
        result = chain.query_with_metadata(request.question)
        
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"]
        )
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
