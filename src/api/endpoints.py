"""FastAPI endpoints for the Intelligent Assistant."""

import logging
from fastapi import APIRouter, HTTPException, Depends
from src.api.schemas import ChatRequest, ChatResponse
from src.retrieval.chain import RAGChain

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency to get RAGChain (singleton pattern or cached)
_rag_chain: RAGChain | None = None

def get_rag_chain() -> RAGChain:
    """Get or initialize the RAGChain instance."""
    global _rag_chain
    if _rag_chain is None:
        try:
            logger.info("Initializing RAGChain for API...")
            _rag_chain = RAGChain()
        except Exception as e:
            logger.error(f"Failed to initialize RAGChain: {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error: Could not initialize RAG system.")
    return _rag_chain

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "Intelligent Assistant API"}

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, chain: RAGChain = Depends(get_rag_chain)):
    """
    Process a user question about cultural events and return a response with sources.
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
