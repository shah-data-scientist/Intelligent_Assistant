"""LLM client for response generation - supports Mistral and Google Gemini."""

import logging
from typing import Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
    before_sleep_log
)
from pybreaker import CircuitBreaker, CircuitBreakerError

from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

from src.config import settings

logger = logging.getLogger(__name__)

# Circuit breaker for LLM calls (fail fast if API is down)
# DISABLED for development/testing - was causing persistent "rate limit" errors
# by blocking all requests after initial failures, even across provider switches.
# To re-enable for production: set ENABLE_CIRCUIT_BREAKER=true in .env
_ENABLE_CIRCUIT_BREAKER = getattr(settings, 'enable_circuit_breaker', False)

if _ENABLE_CIRCUIT_BREAKER:
    llm_breaker = CircuitBreaker(
        fail_max=5,  # Open circuit after 5 failures
        reset_timeout=60,  # Try again after 60 seconds
        name="llm_breaker"
    )
    logger.info("Circuit breaker ENABLED for LLM calls")
else:
    llm_breaker = None
    logger.info("Circuit breaker DISABLED for LLM calls (development mode)")


def is_retryable_llm_error(exception: Exception) -> bool:
    """Check if an LLM error should be retried.

    Retries on:
    - 429 rate limit errors (Google: RESOURCE_EXHAUSTED, Mistral: rate limit)
    - 500/502/503 server errors
    - Connection errors
    """
    error_str = str(exception).lower()
    return (
        # Rate limit errors
        "429" in error_str or
        "resource_exhausted" in error_str or
        "resource exhausted" in error_str or  # Google's plain text variant
        ("rate" in error_str and "limit" in error_str) or
        "too many requests" in error_str or
        "quota" in error_str or
        # Server errors
        "500" in error_str or
        "502" in error_str or
        "503" in error_str or
        "internal server error" in error_str or
        "bad gateway" in error_str or
        "service unavailable" in error_str or
        # Connection errors
        ("connection" in error_str and ("timeout" in error_str or "refused" in error_str))
    )


# Retry decorator for LLM calls - retries on rate limit and server errors
# Reduced to 2 attempts to avoid exhausting quota during rate limiting
llm_retry = retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception(is_retryable_llm_error),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)


def get_chat_llm(
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 2000,
):
    """Get the appropriate LLM based on settings.

    Returns ChatMistralAI, ChatGoogleGenerativeAI, ChatOllama, or ChatHuggingFace based on llm_backend setting.
    Supported backends: "mistral", "google", "huggingface", "ollama"
    """
    backend = settings.llm_backend.lower()

    if backend == "ollama":
        from langchain_ollama import ChatOllama

        model = model or getattr(settings, 'ollama_model', 'mistral')
        base_url = getattr(settings, 'ollama_url', 'http://localhost:11434')

        llm = ChatOllama(
            model=model,
            temperature=temperature,
            num_predict=max_tokens,
            base_url=base_url,
        )
        logger.info(f"Initialized Ollama LLM with model: {model}, temp: {temperature}")
        return llm

    elif backend == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        model = model or "gemini-2.0-flash"  # Stable flash model (2.5 has thinking mode issues)
        llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            max_output_tokens=8192,  # Higher limit for JSON responses with multiple events
            google_api_key=settings.google_api_key,
        )
        logger.info(f"Initialized Google Gemini LLM with model: {model}, temp: {temperature}")
        return llm

    elif backend == "huggingface" or backend == "hf":
        # Use HuggingFace Inference API via wrapper
        import os
        from src.generation.hf_wrapper import HuggingFaceChatWrapper

        model = model or getattr(settings, 'hf_model', 'meta-llama/Llama-3.2-1B-Instruct')
        hf_token = getattr(settings, 'hf_token', None) or os.getenv("HF_TOKEN")

        if not hf_token:
            raise ValueError(
                "HuggingFace token required. Set HF_TOKEN environment variable "
                "or hf_token in settings."
            )

        llm = HuggingFaceChatWrapper(
            model=model,
            token=hf_token,
            temperature=temperature if temperature > 0 else 0.01,
            max_tokens=max_tokens,
        )
        logger.info(f"Initialized HuggingFace LLM with model: {model}, temp: {temperature}")
        return llm

    else:
        # Default to Mistral
        from langchain_mistralai import ChatMistralAI

        model = model or "mistral-small-latest"
        llm = ChatMistralAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.mistral_api_key,
        )
        logger.info(f"Initialized Mistral LLM with model: {model}, temp: {temperature}")
        return llm


class MistralLLM:
    """LLM client for generating responses using LangChain.

    Supports both Mistral and Google Gemini based on settings.
    Name kept as MistralLLM for backward compatibility.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2000,
        api_key: str | None = None,
    ) -> None:
        """Initialize LLM client.

        Args:
            model: Model name (defaults based on backend)
            temperature: Sampling temperature (0.0 for deterministic)
            max_tokens: Maximum number of tokens to generate
            api_key: API key (defaults to settings)
        """
        self.temperature = temperature
        self.max_tokens = max_tokens

        backend = settings.llm_backend.lower()

        if backend == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI

            self.model = model or "gemini-2.0-flash"
            self.api_key = api_key or settings.google_api_key
            self.llm = ChatGoogleGenerativeAI(
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                google_api_key=self.api_key,
            )
            logger.info(f"Initialized Google Gemini LLM with model: {self.model}, temp: {temperature}")
        else:
            from langchain_mistralai import ChatMistralAI

            self.model = model or "mistral-small-latest"
            self.api_key = api_key or settings.mistral_api_key
            self.llm = ChatMistralAI(
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.api_key,
            )
            logger.info(f"Initialized MistralLLM with model: {self.model}, temp: {temperature}")

    @llm_retry
    def generate(
        self,
        messages: list[BaseMessage],
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response from messages with automatic retry.

        Retries up to 2 times with exponential backoff.
        Circuit breaker only active if ENABLE_CIRCUIT_BREAKER=true in settings.

        Args:
            messages: List of chat messages
            **kwargs: Additional arguments for the LLM

        Returns:
            LLM response

        Raises:
            CircuitBreakerError: If circuit is open (when enabled)
            Exception: If all retry attempts fail
        """
        logger.debug(f"Calling LLM generate with {len(messages)} messages")
        if llm_breaker is not None:
            return llm_breaker.call(self.llm.generate, [messages], **kwargs)
        else:
            return self.llm.generate([messages], **kwargs)

    @llm_retry
    def invoke(self, input: Any, **kwargs: Any) -> BaseMessage:
        """Invoke the LLM with a single input with automatic retry.

        Retries up to 2 times with exponential backoff.
        Circuit breaker only active if ENABLE_CIRCUIT_BREAKER=true in settings.

        Args:
            input: LLM input (string, list of messages, etc.)
            **kwargs: Additional arguments

        Returns:
            LLM response message

        Raises:
            CircuitBreakerError: If circuit is open (when enabled)
            Exception: If all retry attempts fail
        """
        logger.debug(f"Calling LLM invoke with input type: {type(input)}")
        if llm_breaker is not None:
            return llm_breaker.call(self.llm.invoke, input, **kwargs)
        else:
            return self.llm.invoke(input, **kwargs)


def main() -> None:
    """CLI entry point for testing LLM."""
    logging.basicConfig(level=logging.INFO)

    llm = MistralLLM()

    # Test simple invocation
    logger.info("Testing simple LLM invocation...")
    response = llm.invoke("Bonjour, comment vas-tu ?")
    logger.info(f"Response: {response.content}")


if __name__ == "__main__":
    main()
