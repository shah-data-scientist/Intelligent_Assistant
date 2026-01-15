"""FastAPI endpoints for the Intelligent Assistant."""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request, Security
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse
from src.api.schemas import ChatRequest, ChatResponse
from src.retrieval.chain import RAGChain
from src.config import settings
from src.security.guardrails import check_safety

logger = logging.getLogger(__name__)
router = APIRouter()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API Key."""
    if api_key != settings.app_api_key:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    return api_key

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

@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
def chat(request: ChatRequest, chain: RAGChain = Depends(get_rag_chain)):
    """
    Process a user question about cultural events and return a response with sources.
    
    Executed synchronously in a thread pool to avoid blocking the asyncio event loop
    with heavy model inference calls.
    """
    try:
        # 1. Security Check
        check_safety(request.question)
        
        logger.info(f"Received chat request: {request.question}")
        
        # 2. RAG Generation
        result = chain.query_with_metadata(request.question)
        
        return ChatResponse(
            answer=result["answer"],
            sources=result["sources"]
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream", dependencies=[Depends(verify_api_key)])
def chat_stream(request: ChatRequest, chain: RAGChain = Depends(get_rag_chain)):
    """
    Stream the response token by token.
    """
    try:
        check_safety(request.question)
        logger.info(f"Received stream request: {request.question}")
        
        return StreamingResponse(
            chain.stream_query(request.question), 
            media_type="text/plain"
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error streaming chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
