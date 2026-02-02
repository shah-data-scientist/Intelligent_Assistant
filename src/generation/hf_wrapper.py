"""HuggingFace Inference API wrapper for LangChain compatibility.

Provides a LangChain-compatible interface using huggingface_hub directly.
Includes robust error handling for HuggingFace-specific issues:
- Model loading delays (cold starts)
- Rate limiting
- Queue timeouts
"""

import logging
import time
from typing import Any, List, Optional

from huggingface_hub import InferenceClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

logger = logging.getLogger(__name__)


# ========================================
# HUGGINGFACE-SPECIFIC ERROR TYPES
# ========================================


class HuggingFaceError(Exception):
    """Base exception for HuggingFace API errors."""

    pass


class HuggingFaceModelLoadingError(HuggingFaceError):
    """Model is currently loading (cold start). Retry after wait."""

    def __init__(self, estimated_time: float = 20.0):
        self.estimated_time = estimated_time
        super().__init__(f"Model is loading. Estimated wait: {estimated_time}s")


class HuggingFaceRateLimitError(HuggingFaceError):
    """Rate limit exceeded."""

    pass


class HuggingFaceQueueError(HuggingFaceError):
    """Request queued or timed out."""

    pass


def is_hf_model_loading_error(error: Exception) -> bool:
    """Check if error is a model loading error (cold start)."""
    error_str = str(error).lower()
    return (
        "model is currently loading" in error_str
        or "is currently loading" in error_str
        or "estimated_time" in error_str
        or "loading" in error_str
        and "model" in error_str
    )


def is_hf_rate_limit_error(error: Exception) -> bool:
    """Check if error is a HuggingFace rate limit error."""
    error_str = str(error).lower()
    return "rate limit" in error_str or "too many requests" in error_str or "429" in error_str or "quota" in error_str


def is_hf_queue_error(error: Exception) -> bool:
    """Check if error is a queue/timeout error."""
    error_str = str(error).lower()
    return "queue" in error_str or "timeout" in error_str or "timed out" in error_str or "503" in error_str


class HuggingFaceChatWrapper(BaseChatModel):
    """LangChain-compatible wrapper for HuggingFace Inference API."""

    model: str = "meta-llama/Llama-3.2-1B-Instruct"
    token: str = ""
    temperature: float = 0.01
    max_tokens: int = 2000
    client: Any = None

    def __init__(
        self,
        model: str = "meta-llama/Llama-3.2-1B-Instruct",
        token: str = "",
        temperature: float = 0.01,
        max_tokens: int = 2000,
        **kwargs: Any,
    ):
        """Initialize HuggingFace wrapper.

        Args:
            model: HuggingFace model ID
            token: HuggingFace API token
            temperature: Sampling temperature (must be > 0 for HF)
            max_tokens: Maximum tokens to generate
        """
        super().__init__(
            model=model,
            token=token,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        self.client = InferenceClient(token=token)
        logger.info(f"Initialized HuggingFaceChatWrapper with model: {model}")

    @property
    def _llm_type(self) -> str:
        """Return LLM type."""
        return "huggingface"

    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        """Convert LangChain messages to HuggingFace format."""
        hf_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                hf_messages.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                hf_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                hf_messages.append({"role": "assistant", "content": msg.content})
            else:
                # Default to user role
                hf_messages.append({"role": "user", "content": str(msg.content)})
        return hf_messages

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response from messages with automatic retry for model loading.

        Args:
            messages: List of chat messages
            stop: Stop sequences (not fully supported)
            run_manager: Callback manager (ignored)
            **kwargs: Additional arguments

        Returns:
            ChatResult with generated response

        Raises:
            HuggingFaceModelLoadingError: If model still loading after retries
            HuggingFaceRateLimitError: If rate limit exceeded
            HuggingFaceQueueError: If request queued/timed out
        """
        hf_messages = self._convert_messages(messages)

        # Retry configuration for model loading (cold starts)
        max_retries = 3
        base_wait = 10  # seconds

        for attempt in range(max_retries):
            try:
                response = self.client.chat_completion(
                    messages=hf_messages,
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                )

                content = response.choices[0].message.content
                message = AIMessage(content=content)
                generation = ChatGeneration(message=message)

                if attempt > 0:
                    logger.info(f"[HF] Request succeeded after {attempt} retry(ies)")

                return ChatResult(generations=[generation])

            except Exception as e:
                error_str = str(e)

                # Handle model loading errors (cold start) - retry with wait
                if is_hf_model_loading_error(e):
                    if attempt < max_retries - 1:
                        wait_time = base_wait * (attempt + 1)
                        logger.warning(
                            f"[HF] Model loading (attempt {attempt + 1}/{max_retries}). "
                            f"Waiting {wait_time}s before retry..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"[HF] Model still loading after {max_retries} attempts")
                        raise HuggingFaceModelLoadingError(estimated_time=30.0)

                # Handle rate limit errors - don't retry, raise immediately
                if is_hf_rate_limit_error(e):
                    logger.error(f"[HF] Rate limit exceeded: {error_str}")
                    raise HuggingFaceRateLimitError(f"HuggingFace rate limit: {error_str}")

                # Handle queue/timeout errors - retry once
                if is_hf_queue_error(e):
                    if attempt < max_retries - 1:
                        wait_time = 5
                        logger.warning(f"[HF] Queue/timeout error, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"[HF] Queue error persists: {error_str}")
                        raise HuggingFaceQueueError(f"HuggingFace queue error: {error_str}")

                # Unknown error - log and raise
                logger.error(f"[HF] API call failed: {e}")
                raise

        # Should not reach here, but just in case
        raise HuggingFaceError("Max retries exceeded")

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> AIMessage:
        """Invoke the LLM with input.

        Args:
            input: String or list of messages
            config: LangChain config (ignored but accepted for compatibility)
            **kwargs: Additional arguments

        Returns:
            AI response message
        """
        if isinstance(input, str):
            messages = [HumanMessage(content=input)]
        elif isinstance(input, list):
            messages = input
        else:
            messages = [HumanMessage(content=str(input))]

        result = self._generate(messages, **kwargs)
        return result.generations[0].message
