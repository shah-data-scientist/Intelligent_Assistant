"""Generation quality evaluation metrics.

This module provides LLM-based and traditional metrics for evaluating generation quality:
- Faithfulness: Does the answer ground to source documents?
- Relevancy: Does the answer address the user's question?
- Language Consistency: Does the answer language match the query language?
"""

import json
import logging
from typing import Any

from src.evaluation.llm_backends import BaseLLMBackend, create_llm_backend

logger = logging.getLogger(__name__)


# LLM-as-a-Judge Prompts
FAITHFULNESS_JUDGE_PROMPT = """You are an expert evaluator assessing whether an AI-generated answer is faithful to the provided source documents.

TASK: Evaluate if the answer's FACTUAL CLAIMS are supported by the sources. Focus on substantive accuracy, not minor formatting differences.

QUERY: {query}

SOURCES:
{sources}

ANSWER:
{answer}

EVALUATION CRITERIA:

✅ ACCEPTABLE (Not hallucinations):
- Information directly stated in sources
- Reasonable paraphrasing of source content
- Formatting differences (e.g., "13/02/2026" vs "February 13, 2026")
- Natural language connectors ("Here are", "I found", "Based on the sources")
- Omitting fields not present in sources (good grounding practice)
- Structural text like bullet points or numbering

❌ HALLUCINATIONS (Penalize these):
- Event names, dates, locations, or URLs NOT in sources
- Biographical information or descriptions NOT in sources
- Specific details (times, prices, performers) NOT in sources
- Placeholder text like "[Not available]" or "[Link unavailable]"
- Inventing event details or combining information incorrectly

OUTPUT (JSON):
{{
  "score": <0.0 to 1.0>,
  "reasoning": "<brief explanation>",
  "violations": ["<specific hallucination 1>", "<specific hallucination 2>", ...]
}}

Score Guidelines:
- 1.0: All factual claims supported by sources, excellent grounding
- 0.8-0.9: Nearly perfect, very minor issues (e.g., one paraphrasing inaccuracy)
- 0.6-0.7: Mostly grounded with 1-2 minor unsupported claims
- 0.4-0.5: Multiple unsupported claims but core facts are correct
- 0.0-0.3: Severe hallucinations or fabricated information

Respond with ONLY the JSON object, no additional text."""


RELEVANCY_JUDGE_PROMPT = """You are an expert evaluator assessing whether an AI-generated answer is relevant and useful to the user's question.

TASK: Evaluate if the answer directly addresses the user's query and provides helpful, actionable information.

QUERY: {query}

ANSWER:
{answer}

EVALUATION CRITERIA:

✅ HIGH RELEVANCY (score 0.75-1.0):
- **EXACT MATCHES (0.9-1.0):** Directly answers ALL parts of the user's query with exact matches
- **PROACTIVE ASSISTANCE (0.75-0.95):** Offers helpful alternatives when exact match not found
  * Provides specific, actionable events (dates, locations, links) even if not exact matches
  * Suggests related events (e.g., affordable events when no free events exist)
  * Proposes broader search criteria (e.g., nearby locations, different time periods)
  * Asks clarifying questions to better help the user
  * Explains what's available and why exact match isn't possible
  * Lists 3+ concrete alternatives with full details
- Well-structured and easy to understand
- Demonstrates understanding of user's intent and attempts to satisfy it

**KEY PRINCIPLE:** If the answer provides 3+ relevant alternatives with actionable details (dates, locations, links) and explains the situation transparently, score 0.75-0.90 even if not exact matches.

⚠️ MEDIUM RELEVANCY (score 0.4-0.7):
- Answers the main question but misses some details
- Provides some actionable information but incomplete
- Addresses most but not all query requirements
- Could be clearer or better organized
- Offers alternatives but with insufficient detail (missing dates/links/locations)
- Mentions alternatives but doesn't actually list events

❌ LOW RELEVANCY (score 0.0-0.4):
- Doesn't answer the question asked at all
- Provides generic or vague information without specifics
- Completely misses key query requirements (wrong location, wrong category, etc.)
- Not actionable or useful to the user
- Simply says "no results" without alternatives or explanation
- Lists events that are completely unrelated to the query

CRITICAL SCORING PRINCIPLES:
1. **Helpful alternatives = HIGH relevancy**: A response offering 3+ relevant alternatives with full details should score 0.75-0.90
2. **Transparency + alternatives = GOOD**: Explaining why exact matches don't exist AND providing alternatives demonstrates high relevancy
3. **Actionable information is key**: Dates, locations, links make alternatives valuable - reward this generously
4. **Proactive effort matters**: Attempting to help with related options shows relevancy even if not perfect matches
5. **Be generous with helpful responses**: If in doubt between 0.70 and 0.80, choose 0.80 for responses that genuinely try to help

SCORING EXAMPLES:
- Query: "Free jazz concerts in February" → Answer offers 4 affordable jazz concerts (with dates, links, prices) + explanation → Score: 0.80-0.90 (high relevancy, excellent alternative)
- Query: "Free family events" → Answer lists 5 paid family events with full details + offers to help search other options → Score: 0.75-0.85 (high relevancy, proactive help)
- Query: "Free family events" → Answer lists 2 vague events without prices + no explanation → Score: 0.50-0.60 (medium, insufficient detail)
- Query: "Free family events" → Answer just says "No free events found" → Score: 0.20-0.30 (low, not helpful)

OUTPUT (JSON):
{{
  "score": <0.0 to 1.0>,
  "reasoning": "<brief explanation>",
  "strengths": ["<strength 1>", "<strength 2>", ...],
  "weaknesses": ["<weakness 1>", "<weakness 2>", ...]
}}

Respond with ONLY the JSON object, no additional text."""


class LLMAsJudge:
    """LLM-based evaluation of generation quality.

    Supports multiple LLM backends:
    - Mistral API (paid, high quality)
    - Hugging Face Inference API (free tier)
    - Ollama (local, completely free)
    """

    def __init__(self, backend: BaseLLMBackend | None = None, backend_type: str = "mistral", **backend_kwargs: Any):
        """Initialize with LLM backend.

        Args:
            backend: Pre-configured LLM backend (takes precedence)
            backend_type: Type of backend if backend not provided ("mistral", "huggingface", "ollama")
            **backend_kwargs: Additional backend-specific parameters

        Examples:
            >>> # Use default Mistral backend
            >>> judge = LLMAsJudge()

            >>> # Use Hugging Face free tier
            >>> judge = LLMAsJudge(backend_type="huggingface", api_token="hf_...")

            >>> # Use local Ollama
            >>> judge = LLMAsJudge(backend_type="ollama", model="mistral")

            >>> # Use custom backend
            >>> backend = create_llm_backend("huggingface", model_id="...")
            >>> judge = LLMAsJudge(backend=backend)
        """
        if backend is not None:
            self.backend = backend
        else:
            self.backend = create_llm_backend(
                backend_type=backend_type, temperature=0.0, **backend_kwargs  # Always deterministic for evaluation
            )

        logger.info(f"Initialized LLMAsJudge with backend: {self.backend.get_name()}")

    def _parse_json_response(self, response: str) -> dict[str, Any]:
        """Parse JSON from LLM response.

        Handles responses that might have markdown code blocks or extra text.

        Args:
            response: LLM response string

        Returns:
            Parsed JSON dictionary

        Raises:
            ValueError: If JSON cannot be parsed
        """
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {response[:200]}")
            raise ValueError(f"Invalid JSON in LLM response: {e}")

    def evaluate_faithfulness(self, query: str, answer: str, sources: list[str] | str) -> dict[str, Any]:
        """Evaluate answer faithfulness to source documents.

        Scores how well the answer grounds to provided sources using LLM-as-a-Judge.

        Args:
            query: User's original question
            answer: AI-generated answer to evaluate
            sources: Source documents (list of strings or single string)

        Returns:
            Dictionary with:
                - score (float): Faithfulness score 0.0-1.0
                - reasoning (str): Explanation of the score
                - violations (list[str]): Specific hallucinations detected

        Example:
            >>> judge = LLMAsJudge()
            >>> result = judge.evaluate_faithfulness(
            ...     "What jazz concerts are available?",
            ...     "There is a Jazz Night concert in Paris on 15/02/2026.",
            ...     ["Title: Jazz Night, City: Paris, Date: 15/02/2026"]
            ... )
            >>> result["score"]
            0.95  # High faithfulness
        """
        # Format sources
        if isinstance(sources, str):
            sources_text = sources
        else:
            sources_text = "\n\n".join(f"Source {i+1}:\n{src}" for i, src in enumerate(sources))

        # Create prompt
        prompt = FAITHFULNESS_JUDGE_PROMPT.format(query=query, sources=sources_text, answer=answer)

        try:
            # Get LLM evaluation
            response_text = self.backend.invoke(prompt)

            # Parse JSON response
            result = self._parse_json_response(response_text)

            # Validate required fields
            if "score" not in result:
                logger.warning("LLM response missing 'score', defaulting to 0.5")
                result["score"] = 0.5

            # Ensure violations is a list
            if "violations" not in result:
                result["violations"] = []
            elif not isinstance(result["violations"], list):
                result["violations"] = [str(result["violations"])]

            # Clamp score to valid range
            result["score"] = max(0.0, min(1.0, float(result["score"])))

            logger.debug(
                f"Faithfulness evaluation: score={result['score']:.2f}, violations={len(result['violations'])}"
            )

            return result

        except Exception as e:
            logger.error(f"Faithfulness evaluation failed: {e}")
            return {"score": 0.5, "reasoning": f"Evaluation failed: {str(e)}", "violations": []}

    def evaluate_relevancy(self, query: str, answer: str) -> dict[str, Any]:
        """Evaluate answer relevancy to the user's question.

        Scores how well the answer addresses the query using LLM-as-a-Judge.

        Args:
            query: User's original question
            answer: AI-generated answer to evaluate

        Returns:
            Dictionary with:
                - score (float): Relevancy score 0.0-1.0
                - reasoning (str): Explanation of the score
                - strengths (list[str]): Strong aspects of the answer
                - weaknesses (list[str]): Areas for improvement

        Example:
            >>> judge = LLMAsJudge()
            >>> result = judge.evaluate_relevancy(
            ...     "Show me jazz concerts",
            ...     "Here are jazz concerts: Jazz Night in Paris on 15/02/2026"
            ... )
            >>> result["score"]
            0.9  # High relevancy
        """
        # Create prompt
        prompt = RELEVANCY_JUDGE_PROMPT.format(query=query, answer=answer)

        try:
            # Get LLM evaluation
            response_text = self.backend.invoke(prompt)

            # Parse JSON response
            result = self._parse_json_response(response_text)

            # Validate required fields
            if "score" not in result:
                logger.warning("LLM response missing 'score', defaulting to 0.5")
                result["score"] = 0.5

            # Ensure lists are present
            if "strengths" not in result:
                result["strengths"] = []
            elif not isinstance(result["strengths"], list):
                result["strengths"] = [str(result["strengths"])]

            if "weaknesses" not in result:
                result["weaknesses"] = []
            elif not isinstance(result["weaknesses"], list):
                result["weaknesses"] = [str(result["weaknesses"])]

            # Clamp score to valid range
            result["score"] = max(0.0, min(1.0, float(result["score"])))

            logger.debug(f"Relevancy evaluation: score={result['score']:.2f}")

            return result

        except Exception as e:
            logger.error(f"Relevancy evaluation failed: {e}")
            return {"score": 0.5, "reasoning": f"Evaluation failed: {str(e)}", "strengths": [], "weaknesses": []}

    def evaluate_language_consistency(self, query: str, answer: str) -> dict[str, Any]:
        """Evaluate language consistency between query and answer.

        Uses heuristic-based language detection (French vs English).

        Args:
            query: User's original question
            answer: AI-generated answer

        Returns:
            Dictionary with:
                - query_language (str): Detected query language ("fr" or "en")
                - answer_language (str): Detected answer language ("fr" or "en")
                - is_consistent (bool): Whether languages match
                - score (float): 1.0 if consistent, 0.0 if not

        Example:
            >>> judge = LLMAsJudge()
            >>> result = judge.evaluate_language_consistency(
            ...     "Concerts de jazz à Paris",
            ...     "Voici des concerts de jazz à Paris"
            ... )
            >>> result["is_consistent"]
            True
        """

        def detect_language(text: str) -> str:
            """Simple heuristic language detection."""
            # French indicators
            french_indicators = ["à", "de", "le", "la", "les", "des", "du", "en", "et", "pour", "dans"]
            # English indicators
            english_indicators = ["the", "and", "for", "in", "on", "at", "with", "of"]

            text_lower = text.lower()

            french_count = sum(1 for word in french_indicators if f" {word} " in f" {text_lower} ")
            english_count = sum(1 for word in english_indicators if f" {word} " in f" {text_lower} ")

            return "fr" if french_count > english_count else "en"

        query_lang = detect_language(query)
        answer_lang = detect_language(answer)
        is_consistent = query_lang == answer_lang

        return {
            "query_language": query_lang,
            "answer_language": answer_lang,
            "is_consistent": is_consistent,
            "score": 1.0 if is_consistent else 0.0,
        }

    def evaluate_generation(self, query: str, answer: str, sources: list[str] | str) -> dict[str, Any]:
        """Comprehensive generation quality evaluation.

        Runs all evaluation metrics and returns combined results.

        Args:
            query: User's original question
            answer: AI-generated answer to evaluate
            sources: Source documents for faithfulness check

        Returns:
            Dictionary with all evaluation results:
                - faithfulness_score (float)
                - relevancy_score (float)
                - language_consistent (bool)
                - quality_score (float): Average of faithfulness and relevancy
                - faithfulness_details (dict)
                - relevancy_details (dict)
                - language_details (dict)

        Example:
            >>> judge = LLMAsJudge()
            >>> result = judge.evaluate_generation(
            ...     "What jazz concerts?",
            ...     "Jazz Night in Paris on 15/02/2026",
            ...     ["Title: Jazz Night, City: Paris, Date: 15/02/2026"]
            ... )
            >>> result["quality_score"]
            0.85
        """
        faithfulness = self.evaluate_faithfulness(query, answer, sources)
        relevancy = self.evaluate_relevancy(query, answer)
        language = self.evaluate_language_consistency(query, answer)

        quality_score = (faithfulness["score"] + relevancy["score"]) / 2

        return {
            "faithfulness_score": faithfulness["score"],
            "relevancy_score": relevancy["score"],
            "language_consistent": language["is_consistent"],
            "quality_score": quality_score,
            "faithfulness_details": faithfulness,
            "relevancy_details": relevancy,
            "language_details": language,
        }
