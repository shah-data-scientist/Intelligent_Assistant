"""LLM backend abstraction for evaluation.

Provides multiple LLM backend options for LLM-as-a-Judge evaluation:
- Mistral API (paid, high quality)
- Hugging Face Inference API (free tier available)
- Ollama (local, completely free)
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseLLMBackend(ABC):
    """Abstract base class for LLM backends."""

    @abstractmethod
    def invoke(self, prompt: str) -> str:
        """Invoke the LLM with a prompt and return the response.

        Args:
            prompt: Input prompt for the LLM

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Get the backend name for logging."""
        pass


class MistralBackend(BaseLLMBackend):
    """Mistral AI backend (requires API key, paid)."""

    def __init__(self, temperature: float = 0.0):
        """Initialize Mistral backend.

        Args:
            temperature: Sampling temperature (0.0 for deterministic)
        """
        from src.generation.llm import MistralLLM

        self.llm = MistralLLM(temperature=temperature)
        logger.info("Initialized Mistral backend for evaluation")

    def invoke(self, prompt: str) -> str:
        """Invoke Mistral API."""
        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)

    def get_name(self) -> str:
        """Get backend name."""
        return "mistral"


class HuggingFaceBackend(BaseLLMBackend):
    """Hugging Face Inference API backend (free tier available).

    Uses the Hugging Face Inference API with serverless models.
    Free tier has rate limits but is sufficient for evaluation.

    Recommended models:
    - mistralai/Mistral-7B-Instruct-v0.2 (good quality, free)
    - meta-llama/Llama-2-7b-chat-hf (good quality, free)
    - HuggingFaceH4/zephyr-7b-beta (good quality, free)
    """

    def __init__(
        self,
        model_id: str = "mistralai/Mistral-7B-Instruct-v0.2",
        api_token: str | None = None,
        temperature: float = 0.0,
        max_new_tokens: int = 500
    ):
        """Initialize Hugging Face backend.

        Args:
            model_id: HF model ID (e.g., "mistralai/Mistral-7B-Instruct-v0.2")
            api_token: HF API token (or set HF_TOKEN env var)
            temperature: Sampling temperature
            max_new_tokens: Maximum tokens to generate
        """
        self.model_id = model_id
        self.api_token = api_token or os.getenv("HF_TOKEN")
        self.temperature = temperature
        self.max_new_tokens = max_new_tokens

        if not self.api_token:
            raise ValueError(
                "Hugging Face API token required. Set HF_TOKEN environment variable "
                "or pass api_token parameter. Get a free token at https://huggingface.co/settings/tokens"
            )

        # Try to import huggingface_hub
        try:
            from huggingface_hub import InferenceClient
            self.client = InferenceClient(token=self.api_token)
            logger.info(f"Initialized Hugging Face backend with model: {model_id}")
        except ImportError:
            raise ImportError(
                "huggingface_hub is required for Hugging Face backend. "
                "Install with: pip install huggingface-hub"
            )

    def invoke(self, prompt: str) -> str:
        """Invoke Hugging Face Inference API."""
        try:
            # Use text_generation for instruct models
            response = self.client.text_generation(
                prompt,
                model=self.model_id,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                return_full_text=False
            )

            return response.strip()

        except Exception as e:
            logger.error(f"Hugging Face API call failed: {e}")
            raise RuntimeError(f"Hugging Face inference failed: {e}")

    def get_name(self) -> str:
        """Get backend name."""
        return f"huggingface:{self.model_id}"


class OllamaBackend(BaseLLMBackend):
    """Ollama backend (local, completely free).

    Requires Ollama to be installed and running locally.
    Install: https://ollama.ai/

    Recommended models:
    - mistral (7B, good quality)
    - llama2 (7B, good quality)
    - phi (2.7B, faster, lower quality)
    """

    def __init__(
        self,
        model: str = "mistral",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0
    ):
        """Initialize Ollama backend.

        Args:
            model: Ollama model name (e.g., "mistral", "llama2")
            base_url: Ollama server URL
            temperature: Sampling temperature
        """
        self.model = model
        self.base_url = base_url
        self.temperature = temperature

        # Try to import ollama or use requests
        try:
            import ollama
            self.client = ollama.Client(host=base_url)
            self._use_ollama_lib = True
            logger.info(f"Initialized Ollama backend with model: {model}")
        except ImportError:
            # Fallback to requests
            import requests
            self._use_ollama_lib = False
            self._requests = requests
            logger.info(f"Initialized Ollama backend (via requests) with model: {model}")

    def invoke(self, prompt: str) -> str:
        """Invoke Ollama local server."""
        try:
            if self._use_ollama_lib:
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    options={
                        "temperature": self.temperature,
                        "num_predict": 500
                    }
                )
                return response['response']
            else:
                # Use requests as fallback
                response = self._requests.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": 500
                        }
                    },
                    timeout=60
                )
                response.raise_for_status()
                return response.json()['response']

        except Exception as e:
            logger.error(f"Ollama API call failed: {e}")
            raise RuntimeError(
                f"Ollama inference failed: {e}. "
                "Make sure Ollama is running (ollama serve) and the model is pulled (ollama pull {self.model})"
            )

    def get_name(self) -> str:
        """Get backend name."""
        return f"ollama:{self.model}"


def create_llm_backend(
    backend_type: str = "mistral",
    temperature: float = 0.0,
    **kwargs: Any
) -> BaseLLMBackend:
    """Factory function to create LLM backend.

    Args:
        backend_type: Type of backend ("mistral", "huggingface", "ollama")
        temperature: Sampling temperature
        **kwargs: Additional backend-specific parameters

    Returns:
        Configured LLM backend instance

    Examples:
        >>> # Use Mistral (paid)
        >>> backend = create_llm_backend("mistral", temperature=0.0)

        >>> # Use Hugging Face (free tier)
        >>> backend = create_llm_backend(
        ...     "huggingface",
        ...     model_id="mistralai/Mistral-7B-Instruct-v0.2",
        ...     api_token="hf_..."
        ... )

        >>> # Use Ollama (local, free)
        >>> backend = create_llm_backend("ollama", model="mistral")
    """
    backend_type = backend_type.lower()

    if backend_type == "mistral":
        return MistralBackend(temperature=temperature)

    elif backend_type == "huggingface" or backend_type == "hf":
        model_id = kwargs.get("model_id", "mistralai/Mistral-7B-Instruct-v0.2")
        api_token = kwargs.get("api_token", None)
        max_new_tokens = kwargs.get("max_new_tokens", 500)
        return HuggingFaceBackend(
            model_id=model_id,
            api_token=api_token,
            temperature=temperature,
            max_new_tokens=max_new_tokens
        )

    elif backend_type == "ollama":
        model = kwargs.get("model", "mistral")
        base_url = kwargs.get("base_url", "http://localhost:11434")
        return OllamaBackend(
            model=model,
            base_url=base_url,
            temperature=temperature
        )

    else:
        raise ValueError(
            f"Unknown backend type: {backend_type}. "
            f"Supported: 'mistral', 'huggingface', 'ollama'"
        )
