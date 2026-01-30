# Evaluation LLM Backends Guide

This guide explains how to configure different LLM backends for the LLM-as-a-Judge evaluation framework.

## Overview

The evaluation framework supports multiple LLM backends to balance cost and quality:

| Backend | Cost | Quality | Speed | Setup Required |
|---------|------|---------|-------|----------------|
| **Mistral** | Paid (~$0.001/query) | Excellent | Fast | API key only |
| **Hugging Face** | Free tier available | Good | Medium | Free API token |
| **Ollama** | Free (local) | Good | Fast | Local install |

## 1. Mistral API (Default)

**Best for:** Production evaluations, highest quality

**Pros:**
- Highest quality evaluations
- Fast API response
- No local setup required

**Cons:**
- Costs money per API call
- Requires API key

**Setup:**

```bash
# Already configured in .env
MISTRAL_API_KEY=your_mistral_key_here
```

**Usage:**

```python
from src.evaluation.metrics.generation import LLMAsJudge

# Default uses Mistral
judge = LLMAsJudge()

# Or explicitly
judge = LLMAsJudge(backend_type="mistral")
```

**Cost Estimate:**
- ~500 tokens per evaluation (prompt + response)
- Mistral pricing: ~$0.001 per 1K tokens
- 50 queries = ~$0.025

---

## 2. Hugging Face Inference API (Free Tier)

**Best for:** Development, frequent evaluations, budget-conscious projects

**Pros:**
- **Free tier available** (rate-limited)
- No local setup required
- Good quality with Mistral-7B or Llama2

**Cons:**
- Rate limits on free tier (~10 requests/min)
- Slightly lower quality than paid Mistral
- Requires HF account

**Setup:**

1. **Get a free Hugging Face token:**
   - Visit: https://huggingface.co/settings/tokens
   - Create a new token (read access is enough)
   - Copy the token (starts with `hf_...`)

2. **Set the token:**

```bash
# Option 1: Environment variable (recommended)
export HF_TOKEN=hf_your_token_here

# Option 2: Add to .env file
HF_TOKEN=hf_your_token_here
```

3. **Install dependencies:**

```bash
poetry add huggingface-hub
```

4. **Configure in src/config.py:**

```python
evaluation_llm_backend = "huggingface"
evaluation_hf_model = "mistralai/Mistral-7B-Instruct-v0.2"  # Recommended
```

**Usage:**

```python
from src.evaluation.metrics.generation import LLMAsJudge

# Using environment variable
judge = LLMAsJudge(backend_type="huggingface")

# Or with explicit token
judge = LLMAsJudge(
    backend_type="huggingface",
    api_token="hf_your_token_here"
)

# Using a different model
judge = LLMAsJudge(
    backend_type="huggingface",
    model_id="meta-llama/Llama-2-7b-chat-hf"
)
```

**Recommended Models (all free):**
- `mistralai/Mistral-7B-Instruct-v0.2` (best quality, recommended)
- `meta-llama/Llama-2-7b-chat-hf` (good alternative)
- `HuggingFaceH4/zephyr-7b-beta` (fast, good quality)

**Rate Limits:**
- Free tier: ~10 requests/minute
- For 50 queries: ~5 minutes
- Pro tier ($9/month): Higher limits

---

## 3. Ollama (Local, Completely Free)

**Best for:** Privacy-sensitive projects, unlimited evaluations, offline work

**Pros:**
- **Completely free** - no API costs
- Unlimited evaluations
- Works offline
- Full privacy (data never leaves your machine)

**Cons:**
- Requires local installation (~4GB download per model)
- Needs decent hardware (8GB+ RAM recommended)
- Slightly slower first run (model loading)

**Setup:**

1. **Install Ollama:**

Visit https://ollama.ai/ and download for your OS.

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows: Download installer from https://ollama.ai/
```

2. **Pull a model:**

```bash
# Recommended: Mistral (7B, good quality)
ollama pull mistral

# Alternative: Llama2 (7B)
ollama pull llama2

# Lightweight: Phi (2.7B, faster but lower quality)
ollama pull phi
```

3. **Start Ollama server:**

```bash
ollama serve
```

Server runs at `http://localhost:11434` by default.

4. **Configure in src/config.py:**

```python
evaluation_llm_backend = "ollama"
evaluation_ollama_model = "mistral"
```

**Usage:**

```python
from src.evaluation.metrics.generation import LLMAsJudge

# Default model (mistral)
judge = LLMAsJudge(backend_type="ollama")

# Different model
judge = LLMAsJudge(backend_type="ollama", model="llama2")

# Custom Ollama server
judge = LLMAsJudge(
    backend_type="ollama",
    model="mistral",
    base_url="http://your-server:11434"
)
```

**Model Recommendations:**
- `mistral`: Best balance of quality and speed (recommended)
- `llama2`: Good alternative, similar quality
- `phi`: Faster but lower quality (for quick tests)

**Hardware Requirements:**
- 8GB RAM minimum
- 16GB RAM recommended
- ~4-7GB disk space per model

---

## Configuration via Environment

You can also configure backends via environment variables in `.env`:

```bash
# Backend selection
EVALUATION_LLM_BACKEND=huggingface  # or "mistral", "ollama"

# Hugging Face settings
HF_TOKEN=hf_your_token_here
EVALUATION_HF_MODEL=mistralai/Mistral-7B-Instruct-v0.2

# Ollama settings
EVALUATION_OLLAMA_MODEL=mistral
EVALUATION_OLLAMA_URL=http://localhost:11434
```

## Programmatic Configuration

```python
from src.config import settings
from src.evaluation.metrics.generation import LLMAsJudge

# Method 1: Use settings
judge = LLMAsJudge(
    backend_type=settings.evaluation_llm_backend
)

# Method 2: Override settings
judge = LLMAsJudge(
    backend_type="huggingface",  # Override
    model_id="meta-llama/Llama-2-7b-chat-hf"
)

# Method 3: Custom backend
from src.evaluation.llm_backends import create_llm_backend

backend = create_llm_backend(
    "huggingface",
    model_id="mistralai/Mistral-7B-Instruct-v0.2",
    api_token="hf_..."
)
judge = LLMAsJudge(backend=backend)
```

## Running Evaluations

Once configured, evaluations work identically regardless of backend:

```python
from src.evaluation.metrics.generation import LLMAsJudge

# Initialize with your chosen backend
judge = LLMAsJudge(backend_type="huggingface")  # or "mistral", "ollama"

# Evaluate faithfulness
result = judge.evaluate_faithfulness(
    query="What jazz concerts are available?",
    answer="There is a Jazz Night concert in Paris on 15/02/2026.",
    sources=["Title: Jazz Night\nCity: Paris\nDate: 15/02/2026"]
)

print(f"Faithfulness score: {result['score']:.2f}")
print(f"Violations: {result['violations']}")
```

## Troubleshooting

### Hugging Face Issues

**Error: "429 Too Many Requests"**
- You're hitting rate limits
- Wait a minute between batches
- Consider Pro tier for higher limits

**Error: "Authentication failed"**
- Check your HF_TOKEN is set correctly
- Verify token has read permissions
- Generate a new token if needed

### Ollama Issues

**Error: "Connection refused"**
- Ollama server not running
- Start with: `ollama serve`
- Check server is at `http://localhost:11434`

**Error: "Model not found"**
- Model not pulled
- Run: `ollama pull mistral`
- Check available models: `ollama list`

**Slow performance:**
- First run loads model (~10-30s)
- Subsequent runs are faster
- Consider smaller model (phi) for testing

## Recommendations

**For Development:**
- Use **Hugging Face** (free tier) or **Ollama** (local)
- Fast iteration, no costs

**For Production:**
- Use **Mistral API** for best quality
- Costs are minimal (~$0.025 for 50 queries)

**For Privacy:**
- Use **Ollama** (local)
- Data never leaves your machine

**For Budget:**
- Use **Hugging Face** free tier
- Rate-limited but free forever

## Backend Comparison Matrix

| Feature | Mistral | Hugging Face | Ollama |
|---------|---------|--------------|--------|
| Cost | ~$0.001/query | Free (rate-limited) | Free (unlimited) |
| Setup Time | 1 min | 5 min | 15 min |
| Quality | Excellent | Good | Good |
| Speed | Fast (2-5s) | Medium (5-10s) | Fast (2-8s) |
| Rate Limits | High | 10/min (free) | None |
| Privacy | Cloud | Cloud | Local |
| Offline | No | No | Yes |
| Hardware | None | None | 8GB+ RAM |

## Example: Switch All Tests to Free Backend

```python
# In your test file or evaluation script
import os

# Set environment before imports
os.environ["EVALUATION_LLM_BACKEND"] = "huggingface"
os.environ["HF_TOKEN"] = "hf_your_token_here"

from src.evaluation.metrics.generation import LLMAsJudge

# Now all LLMAsJudge instances will use Hugging Face
judge = LLMAsJudge()
```

## Next Steps

1. Choose your backend based on needs
2. Follow setup instructions above
3. Update `src/config.py` or set environment variables
4. Run evaluations as normal

For questions or issues, check the troubleshooting section or file an issue on GitHub.
