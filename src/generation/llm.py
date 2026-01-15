"""Mistral LLM client for response generation."""

import logging
from typing import Any

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult

from src.config import settings

logger = logging.getLogger(__name__)


class MistralLLM:
    """Mistral LLM client for generating responses using LangChain."""

    def __init__(
        self,
        model: str = "mistral-small-latest",
        temperature: float = 0.0,
        max_tokens: int = 500,
        api_key: str | None = None,
    ) -> None:
        """Initialize Mistral LLM client.

        Args:
            model: Mistral model name
            temperature: Sampling temperature (0.0 for deterministic)
            max_tokens: Maximum number of tokens to generate
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

    def generate(
        self,
        messages: list[BaseMessage],
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response from messages.

        Args:
            messages: List of chat messages
            **kwargs: Additional arguments for the LLM

        Returns:
            LLM response
        """
        return self.llm.generate([messages], **kwargs)

    async def agenerate(
        self,
        messages: list[BaseMessage],
        **kwargs: Any,
    ) -> ChatResult:
        """Generate response from messages asynchronously.

        Args:
            messages: List of chat messages
            **kwargs: Additional arguments for the LLM

        Returns:
            LLM response
        """
        return await self.llm.agenerate([messages], **kwargs)

    def invoke(self, input: Any, **kwargs: Any) -> BaseMessage:
        """Invoke the LLM with a single input.

        Args:
            input: LLM input (string, list of messages, etc.)
            **kwargs: Additional arguments

        Returns:
            LLM response message
        """
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
