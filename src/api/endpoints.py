"""FastAPI endpoints for the Intelligent Assistant."""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Request, Security
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.api.schemas import ChatRequest, ChatResponse, FeedbackRequest
from src.retrieval.chain import RAGChain
from src.config import settings
from src.security.guardrails import check_safety, SecurityException, SessionBlockedException
from src.security.sanitization import scan_for_pii
from src.utils.tracing import generate_trace_id, clear_trace_id

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

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
async def health_check(request: Request):
    """Health check endpoint."""
    rag_initialized = hasattr(request.app.state, "rag_chain") and request.app.state.rag_chain is not None
    return {
        "status": "ok" if rag_initialized else "error",
        "rag_system": "initialized" if rag_initialized else "not_initialized",
        "service": "Intelligent Assistant API",
    }


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
@limiter.limit("20/minute")  # 20 requests per minute per IP for chat endpoint
def chat(request: Request, chat_request: ChatRequest, chain: RAGChain = Depends(get_rag_chain)):
    """
    Process a user question about cultural events and return a response with sources.

    Rate limited to 20 requests per minute per IP address.
    Executed synchronously in a thread pool to avoid blocking the asyncio event loop
    with heavy model inference calls.
    """
    # Generate trace ID for this request
    trace_id = generate_trace_id()

    try:
        # 1. Security Check (with session blocking)
        check_safety(chat_request.question, session_id=chat_request.session_id)

        logger.info(f"Received chat request: {chat_request.question} (session: {chat_request.session_id})")

        # 2. RAG Generation
        result = chain.query_with_metadata(
            chat_request.question,
            session_id=chat_request.session_id,
            language=chat_request.language,  # Auto-detected if None
        )

        # 3. PII Scanning and Sanitization
        answer_text = result["answer"]
        pii_result = scan_for_pii(answer_text, redact=True)
        sanitized_answer = pii_result["sanitized_text"]
        had_pii = pii_result["has_pii"]

        if had_pii:
            logger.warning("PII detected and redacted from response")

        # 4. Build response with trace ID
        response = ChatResponse(
            answer=sanitized_answer,
            sources=result["sources"],
            structured_events=result.get("structured_events", []),
            message_id=result.get("message_id"),
            needs_clarification=result.get("needs_clarification", False),
            clarifying_questions=result.get("clarifying_questions", []),
        )

        logger.info("Chat request completed successfully")
        return response

    except SessionBlockedException as sbe:
        # Session is blocked due to previous violation - return 403 Forbidden
        logger.warning(f"Blocked session attempted request: {sbe}")
        raise HTTPException(status_code=403, detail=str(sbe))
    except SecurityException as se:
        # Security violation - return 400 Bad Request (session is now blocked)
        logger.warning(f"Security guardrail triggered: {se}")
        raise HTTPException(status_code=400, detail=str(se))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clear trace ID after request
        clear_trace_id()


@router.post("/feedback", dependencies=[Depends(verify_api_key)])
def post_feedback(request: FeedbackRequest, chain: RAGChain = Depends(get_rag_chain)):
    """
    Submit user feedback for a specific message.
    """
    try:
        chain.chat_storage.add_feedback(
            message_id=request.message_id, is_positive=request.is_positive, comment=request.comment
        )
        return {"status": "success", "message": "Feedback submitted"}
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


@router.get("/metrics")
async def get_metrics():
    """
    Get system metrics including circuit breaker state.

    Returns health information about the LLM circuit breaker and other
    system components for monitoring and alerting.
    """
    from src.generation.llm import llm_breaker

    # Get circuit breaker state
    breaker_state = {
        "name": llm_breaker.name,
        "state": str(llm_breaker.current_state),
        "failure_count": llm_breaker.fail_counter,
        "failure_threshold": llm_breaker.fail_max,
        "reset_timeout": llm_breaker.reset_timeout,
    }

    # Add last failure time if available
    if hasattr(llm_breaker, "_last_failure"):
        breaker_state["last_failure_time"] = str(llm_breaker._last_failure)

    return {"status": "ok", "circuit_breaker": breaker_state, "timestamp": datetime.now().isoformat()}
