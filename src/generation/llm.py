"""Mistral LLM client for response generation."""

import logging
from typing import Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from pybreaker import CircuitBreaker, CircuitBreakerError

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

from src.config import settings

logger = logging.getLogger(__name__)

# Circuit breaker for LLM calls (fail fast if Mistral API is down)
llm_breaker = CircuitBreaker(
    fail_max=5,  # Open circuit after 5 failures
    reset_timeout=60,  # Try again after 60 seconds
    name="mistral_llm_breaker"
)

# Retry decorator for LLM calls
llm_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)


class MistralLLM:
    """Mistral LLM client for generating responses using LangChain."""

    def __init__(
        self,
        model: str = "mistral-small-latest",
        temperature: float = 0.0,
        max_tokens: int = 2000,
        api_key: str | None = None,
    ) -> None:
        """Initialize Mistral LLM client.

        Args:
            model: Mistral model name
            temperature: Sampling temperature (0.0 for deterministic)
            max_tokens: Maximum number of tokens to generate (increased to 2000 for complete answers)
            api_key: Mistral API key (defaults to settings)
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key or settings.mistral_api_key

        self.llm = ChatMistralAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=self.api_key,
        )
        logger.info(f"Initialized MistralLLM with model: {model}, temp: {temperature}")

    @llm_retry
    def generate(
        self,
        messages: list[BaseMessage],
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response from messages with automatic retry and circuit breaker.

        Retries up to 3 times with exponential backoff (1s, 2s, 4s, max 10s).
        Circuit breaker opens after 5 consecutive failures and closes after 60s.

        Args:
            messages: List of chat messages
            **kwargs: Additional arguments for the LLM

        Returns:
            LLM response

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If all retry attempts fail
        """
        logger.debug(f"Calling LLM generate with {len(messages)} messages")
        return llm_breaker.call(self.llm.generate, [messages], **kwargs)

    async def agenerate(
        self,
        messages: list[BaseMessage],
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response from messages asynchronously with automatic retry.

        Retries up to 3 times with exponential backoff.

        Args:
            messages: List of chat messages
            **kwargs: Additional arguments for the LLM

        Returns:
            LLM response

        Raises:
            Exception: If all retry attempts fail
        """
        logger.debug(f"Calling LLM agenerate with {len(messages)} messages")
        # Note: tenacity retry decorator works with async functions
        @llm_retry
        async def _agenerate_with_retry():
            return await self.llm.agenerate([messages], **kwargs)

        return await _agenerate_with_retry()

    @llm_retry
    def invoke(self, input: Any, **kwargs: Any) -> BaseMessage:
        """Invoke the LLM with a single input with automatic retry and circuit breaker.

        Retries up to 3 times with exponential backoff.
        Circuit breaker opens after 5 consecutive failures.

        Args:
            input: LLM input (string, list of messages, etc.)
            **kwargs: Additional arguments

        Returns:
            LLM response message

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If all retry attempts fail
        """
        logger.debug(f"Calling LLM invoke with input type: {type(input)}")
        return llm_breaker.call(self.llm.invoke, input, **kwargs)


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
