"""Security guardrails for the RAG system."""

import logging
import re
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Patterns indicative of prompt injection or malicious intent
# In a real system, use a model like NVIDIA NeMo or Lakera Guard
MALICIOUS_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all instructions",
    r"delete database",
    r"drop table",
    r"system override",
    r"you are now",  # Jailbreak attempt
    r"developer mode",
]

TOXIC_KEYWORDS = [
    "hate", "kill", "death", "stupid", "idiot" # Very basic list for POC
]

def check_safety(query: str) -> None:
    """Check if the query contains malicious patterns or toxic content.

    Args:
        query: User input string

    Raises:
        HTTPException: If safety check fails
    """
    query_lower = query.lower()

    # Check for prompt injection patterns
    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, query_lower):
            logger.warning(f"Blocked malicious query: {query}")
            raise HTTPException(
                status_code=400, 
                detail="Request rejected: Potential prompt injection detected."
            )

    # Check for basic toxicity
    # (Note: This is a placeholder for a real toxicity classifier)
    for word in TOXIC_KEYWORDS:
        if f" {word} " in f" {query_lower} ":
            logger.warning(f"Blocked toxic query: {query}")
            raise HTTPException(
                status_code=400, 
                detail="Request rejected: Inappropriate language detected."
            )
            
    logger.info("Query passed safety check.")
