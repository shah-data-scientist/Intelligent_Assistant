"RAG orchestration chain for cultural events with history."

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import date, timedelta

from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableBranch
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from src.models.vector_store import EventVectorStore
from src.generation.llm import MistralLLM
from src.generation.prompts import get_rag_prompt, get_contextualize_q_prompt, get_metadata_extraction_prompt, get_query_refinement_prompt
from src.retrieval.retriever import EventRetriever
from src.retrieval.cache import QueryCache
from src.retrieval.manager import RetrievalManager
from src.data.chat_history import SQLiteChatMessageHistory
from src.data.storage import EventStorage
from src.data.chat_storage import ChatStorage
from src.security.guardrails import check_safety
from src.utils.dates import parse_natural_date
from src.config import settings

logger = logging.getLogger(__name__)

# ========================================
# SPECIAL QUERY HANDLERS
# ========================================
# These handle greetings, off-topic queries, and capability questions
# BEFORE the RAG chain is invoked.

# Greeting patterns (French and English)
GREETING_PATTERNS = [
    r"^(bonjour|bonsoir|salut|coucou|hello|hi|hey|good\s*(morning|afternoon|evening))[\s\!\.\?]*$",
    r"^(bonjour|bonsoir|salut|coucou|hello|hi|hey)[\s\!\.\?]*$",
]

# Capability/meta question patterns
CAPABILITY_PATTERNS = [
    r"(what|que|qu'est-ce que)\s*(can|peux|pouvez|tu peux)\s*(you|tu)\s*(do|faire|help|aider)",
    r"(what|que|quelles)\s*(are|sont)\s*(your|tes|vos)\s*(capabilities|capacit|fonctions)",
    r"(tell me|dis-moi|parle-moi)\s*(about|de)\s*(yourself|toi)",
    r"(who|qui)\s*(are|es)\s*(you|tu)",
    r"(help|aide|comment).*\?$",
    r"^(help|aide)[\s\!\.\?]*$",
]

# Off-topic patterns (things Lumi cannot help with)
OFF_TOPIC_PATTERNS = [
    r"(weather|meteo|m\u00e9t\u00e9o|temperature|temp\u00e9rature)",
    r"(write|ecris|\u00e9cris).*(poem|poeme|po\u00e8me|story|histoire|essay)",
    r"(translate|traduis|traduire)",
    r"(recipe|recette|cook|cuisine|cuisiner)",
    r"(math|calcul|equation|\u00e9quation|calculate|calculer)",
    r"(code|program|programme|python|javascript)",
    r"(news|actualit|politique|politics)",
    r"(medical|m\u00e9dical|health|sant\u00e9|doctor|m\u00e9decin)",
    r"(legal|juridique|lawyer|avocat)",
    r"(stock|bourse|invest|finance)",
]

# Greeting responses (bilingual) - Uses centralized config for chatbot name
GREETING_RESPONSES = {
    "fr": f"""Bonjour ! Je suis **{settings.chatbot_name}**, {settings.chatbot_tagline_fr}.

Je peux vous aider a decouvrir des evenements culturels : concerts, expositions, theatre, festivals et plus encore !

**Essayez de me demander :**
- "Concerts de jazz a Paris ce week-end"
- "Expositions gratuites en fevrier"
- "Evenements pour enfants a Versailles"

Qu'est-ce qui vous ferait plaisir aujourd'hui ?""",

    "en": f"""Hello! I'm **{settings.chatbot_name}**, {settings.chatbot_tagline_en}.

I can help you discover cultural events: concerts, exhibitions, theater, festivals and more!

**Try asking me:**
- "Jazz concerts in Paris this weekend"
- "Free exhibitions in February"
- "Family events in Versailles"

What would you like to explore today?"""
}

# Capability responses (bilingual) - Uses centralized config for chatbot name
CAPABILITY_RESPONSES = {
    "fr": f"""Je suis **{settings.chatbot_name}**, {settings.chatbot_tagline_fr} !

**Ce que je peux faire :**
- Trouver des evenements culturels (concerts, theatre, expositions, festivals)
- Filtrer par ville, date, categorie, prix (gratuit/payant)
- Suggerer des alternatives si rien ne correspond exactement
- Repondre en francais ou en anglais

**Ce que je ne peux PAS faire :**
- Donner la meteo, ecrire des poemes, ou traduire
- Reserver des billets ou faire des achats
- Repondre a des questions hors du domaine culturel

**Exemples de questions :**
- "Concerts de jazz a Paris en fevrier"
- "Expositions gratuites ce week-end"
- "Evenements pour enfants a Versailles"

Comment puis-je vous aider ?""",

    "en": f"""I'm **{settings.chatbot_name}**, {settings.chatbot_tagline_en}!

**What I can do:**
- Find cultural events (concerts, theater, exhibitions, festivals)
- Filter by city, date, category, price (free/paid)
- Suggest alternatives if nothing matches exactly
- Answer in French or English

**What I canNOT do:**
- Give weather forecasts, write poems, or translate
- Book tickets or make purchases
- Answer questions outside the cultural domain

**Example questions:**
- "Jazz concerts in Paris in February"
- "Free exhibitions this weekend"
- "Family events in Versailles"

How can I help you?"""
}

# Off-topic responses (bilingual)
OFF_TOPIC_RESPONSES = {
    "fr": """Je suis desole, mais je suis specialisee dans les evenements culturels de l'Ile-de-France.

Je ne peux pas vous aider avec cette demande, mais je serais ravie de vous aider a trouver :
- Des concerts, spectacles ou festivals
- Des expositions d'art ou des musees
- Des pieces de theatre ou des spectacles de danse
- Des evenements pour enfants ou en famille

Y a-t-il un evenement culturel que vous aimeriez decouvrir ?""",

    "en": """I'm sorry, but I specialize in cultural events in Ile-de-France.

I can't help with that request, but I'd be happy to help you find:
- Concerts, shows, or festivals
- Art exhibitions or museums
- Theater plays or dance performances
- Family or children's events

Is there a cultural event you'd like to discover?"""
}


def detect_language_from_query(query: str) -> str:
    """Detect language from query (simple heuristic)."""
    french_indicators = ["bonjour", "salut", "coucou", "merci", "s'il", "qu'est", "evenement", "cherche", "trouve", "veux", "peux"]
    query_lower = query.lower()
    french_count = sum(1 for word in french_indicators if word in query_lower)
    return "fr" if french_count >= 1 else "en"


def sanitize_text_for_encoding(text: str) -> str:
    """Remove emojis and problematic Unicode characters to prevent encoding errors.

    This function strips emojis and other special Unicode characters that can cause
    'charmap' codec errors on Windows systems.
    """
    if not text:
        return text

    # Remove emojis and other special Unicode characters
    # Keep only basic Latin, Latin Extended, and common punctuation
    sanitized = []
    for char in text:
        code_point = ord(char)
        # Keep ASCII, Latin-1, Latin Extended, and common symbols
        if code_point < 0x2000 or (0x2000 <= code_point < 0x2100):  # General punctuation
            sanitized.append(char)
        elif code_point in (0x2014, 0x2013, 0x2018, 0x2019, 0x201C, 0x201D):  # Smart quotes/dashes
            # Replace with ASCII equivalents
            replacements = {0x2014: '-', 0x2013: '-', 0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"'}
            sanitized.append(replacements.get(code_point, char))
        elif code_point >= 0x1F000:  # Emoji ranges
            continue  # Skip emojis
        else:
            sanitized.append(char)

    return ''.join(sanitized)


def check_special_query(query: str, language: Optional[str] = None) -> Optional[Tuple[str, str]]:
    """Check if query is a special case (greeting, capability, off-topic).

    Args:
        query: The user query
        language: Optional language code ("fr" or "en")

    Returns:
        Tuple of (response_text, query_type) if special query detected, None otherwise
    """
    query_clean = query.strip().lower()

    # Auto-detect language if not provided
    if language is None:
        language = detect_language_from_query(query)

    # Check greetings (exact match for short queries)
    for pattern in GREETING_PATTERNS:
        if re.match(pattern, query_clean, re.IGNORECASE):
            return (GREETING_RESPONSES[language], "greeting")

    # Check capability questions
    for pattern in CAPABILITY_PATTERNS:
        if re.search(pattern, query_clean, re.IGNORECASE):
            return (CAPABILITY_RESPONSES[language], "capability")

    # Check off-topic queries
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, query_clean, re.IGNORECASE):
            return (OFF_TOPIC_RESPONSES[language], "off_topic")

    return None

class SimpleSummaryBufferMemory:
    """Custom implementation of Summary Buffer Memory with actual LLM summarization."""
    
    def __init__(self, llm, chat_memory, max_token_limit=1000, memory_key="chat_history"):
        self.llm = llm
        self.chat_memory = chat_memory
        self.max_token_limit = max_token_limit
        self.memory_key = memory_key
        self.summary_key = "history_summary"
        
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, List[BaseMessage]]:
        """Load history, summarizing older messages if the list is too long."""
        all_messages = self.chat_memory.messages
        
        if len(all_messages) > 10:
            to_summarize = all_messages[:-10]
            to_keep = all_messages[-10:]
            history_str = "\n".join([f"{m.type}: {m.content}" for m in to_summarize])
            
            try:
                summary_prompt = f"Summarize the key facts and user preferences from this cultural events chat history in 2-3 sentences:\n\n{history_str}"
                summary = self.llm.invoke(summary_prompt).content
                context_message = SystemMessage(content=f"Summary of previous conversation: {summary}")
                return {self.memory_key: [context_message] + to_keep}
            except Exception as e:
                logger.warning(f"Summarization failed: {e}")
                return {self.memory_key: all_messages[-20:]}
            
        return {self.memory_key: all_messages}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        pass

class RAGChain:
    """Orchestrator for the Cultural Events RAG system with Summary Buffer Memory."""

    def __init__(
        self,
        vector_store: EventVectorStore | None = None,
        llm: MistralLLM | None = None,
        k: int = 8,
        chat_storage: ChatStorage | None = None,
        enable_cache: bool = True,
        cache_ttl_minutes: int = 60,
        enable_reranking: bool = True,
    ) -> None:
        """Initialize the RAG chain."""
        self.vector_store = vector_store or EventVectorStore()
        try:
            self.vector_store.load_index()
        except Exception as e:
            logger.warning(f"Could not load FAISS index: {e}.")

        self.llm = llm or MistralLLM()
        self.chat_storage = chat_storage or ChatStorage()
        self.k = k
        self.enable_reranking = enable_reranking

        # Initialize deterministic retrieval manager
        self.retrieval_manager = RetrievalManager(self.vector_store, k=k)

        self.cache = QueryCache(ttl_minutes=cache_ttl_minutes) if enable_cache else None

        self.reranker = None
        if enable_reranking:
            from src.retrieval.reranker import get_reranker
            self.reranker = get_reranker()
        
        # Chains
        self.extraction_chain = get_metadata_extraction_prompt() | self.llm.llm.bind(response_format={"type": "json_object"}) | JsonOutputParser()
        self.refinement_chain = get_query_refinement_prompt() | self.llm.llm | StrOutputParser()
        self.retriever = EventRetriever(vector_store=self.vector_store, k=k)
        
        try:
            total_events_val = self.vector_store.storage.count_events()
            min_date, max_date = self.vector_store.storage.get_date_range()
            date_range_val = f"{min_date.strftime('%Y-%m-%d') if min_date else '?'} to {max_date.strftime('%Y-%m-%d') if max_date else '?'}"
        except:
            total_events_val = "Unknown"
            date_range_val = "Unknown"

        current_date_val = "2026-01-24" # Reference date

        # 1. Prepare Inputs
        def prepare_inputs(inputs):
            history = inputs.get("chat_history", [])
            q = inputs["input"]
            if not history or len(history) < 2:
                return {"q": q, "raw_q": q, "history": []}
            try:
                reformulation_chain = get_contextualize_q_prompt() | self.llm.llm | StrOutputParser()
                new_q = reformulation_chain.invoke({"input": q, "chat_history": history})
                return {"q": new_q, "raw_q": q, "history": history}
            except:
                return {"q": q, "raw_q": q, "history": history}

        # 2. Refined Hybrid Retrieval
        def retrieve_docs_hybrid(inputs):
            input_query = inputs["q"]
            raw_query = inputs["raw_q"]
            history = inputs["history"]
            
            try:
                # 1. Refine Query (Typos)
                refined_query = self.refinement_chain.invoke({"question": input_query})
                
                # 2. Extract Intent (Filters)
                raw_filters = self.extraction_chain.invoke({"question": refined_query, "chat_history": history})
                intent = self.retrieval_manager.parse_intent(raw_filters)
                
                # 3. Execute Multi-Stage Search
                result = self.retrieval_manager.execute_search(refined_query, intent)
                
                return {
                    "docs": result["docs"],
                    "filters": raw_filters,
                    "actual_k": result["total_count"],
                    "total_in_database": result.get("total_in_database", result["total_count"]),
                    "filters_applied": result.get("filters_applied", {})
                }
            except Exception as e:
                logger.error(f"Manager retrieval failed: {e}", exc_info=True)
                return {"docs": [], "filters": {}, "actual_k": 0}

        def format_docs(docs, filters):
            if not docs:
                return "NO RELEVANT EVENTS FOUND.", 0
            
            formatted = []
            system_notes = []
            source_num = 1
            for doc in docs:
                meta = doc.metadata
                if "nearby_date_note" in meta:
                    system_notes.append(meta["nearby_date_note"])
                if meta.get("match_type") == "System": continue
                
                header = f"=== SOURCE {source_num} (Title: {meta.get('title')}, City: {meta.get('city')}, Date: {meta.get('start_date')}, Match: {meta.get('match_type')}, Distance: {meta.get('distance_km', 0):.1f}km) ==="
                formatted.append(f"{header}\n{doc.page_content}")
                source_num += 1
            
            final_text = ""
            if system_notes:
                final_text += "SYSTEM NOTES:\n" + "\n".join(set(system_notes)) + "\n\n"
            final_text += "\n\n".join(formatted)
            return final_text, len(formatted)

        # 3. Chain Construction
        def select_prompt(x):
            """Select language-specific prompt based on input language parameter."""
            lang = x.get("language", "fr")  # Default to French
            return get_rag_prompt(language=lang)

        self.rag_chain = (
            RunnablePassthrough.assign(
                retrieved_data=RunnableLambda(prepare_inputs) | retrieve_docs_hybrid,
                total_events=lambda _: str(total_events_val),
                date_range=lambda _: date_range_val,
                current_date=lambda _: current_date_val
            )
            .assign(
                formatting_results=lambda x: format_docs(x["retrieved_data"]["docs"], x["retrieved_data"]["filters"])
            )
            .assign(
                answer=(
                    RunnablePassthrough.assign(
                        context=lambda x: x["formatting_results"][0],
                        k=lambda x: str(x["formatting_results"][1]),
                        today=lambda x: x["current_date"],
                        total_matching=lambda x: str(x["retrieved_data"].get("total_in_database", x["formatting_results"][1])),
                        filters_applied=lambda x: str(x["retrieved_data"].get("filters_applied", {}))
                    )
                    | RunnableLambda(select_prompt)
                    | self.llm.llm.bind(response_format={"type": "json_object"})
                    | JsonOutputParser()
                ),
                context=lambda x: x["retrieved_data"]["docs"]
            )
        )

    def _get_memory(self, session_id: str) -> SimpleSummaryBufferMemory:
        chat_memory = SQLiteChatMessageHistory(session_id=session_id, storage=self.chat_storage)
        return SimpleSummaryBufferMemory(llm=self.llm.llm, chat_memory=chat_memory)

    def query(self, question: str, session_id: str = "default_session") -> str:
        result = self.query_with_metadata(question, session_id)
        return result["answer"]

    def _is_statistical_query(self, question: str) -> bool:
        q = question.lower()
        stat_kw = ['how many', 'combien', 'number of', 'count', 'total']
        entity_kw = ['events', 'événements']
        return any(k in q for k in stat_kw) and any(k in q for k in entity_kw)

    def query_with_metadata(self, question: str, session_id: str = "default_session", language: str = None) -> Dict[str, Any]:
        logger.info(f"Query: {question}")
        check_safety(question)

        # Default to French if language not specified, or auto-detect
        if language is None:
            language = detect_language_from_query(question)

        # Check for special queries (greetings, capabilities, off-topic)
        special_result = check_special_query(question, language)
        if special_result:
            response_text, query_type = special_result
            logger.info(f"Special query detected: {query_type}")
            # Save to chat history (LangChain memory)
            memory = self._get_memory(session_id)
            memory.chat_memory.add_message(HumanMessage(content=question))
            memory.chat_memory.add_message(AIMessage(content=response_text))
            # Save to persistent storage and get message_id
            self.chat_storage.add_chat_message(session_id, "user", question)
            message_id = self.chat_storage.add_chat_message(session_id, "assistant", response_text)
            return {
                "answer": response_text,
                "sources": [],
                "structured_events": [],
                "message_id": message_id,
                "query_type": query_type
            }

        if self._is_statistical_query(question):
            stat_response = "I am designed to find events, not provide statistics."
            self.chat_storage.add_chat_message(session_id, "user", question)
            message_id = self.chat_storage.add_chat_message(session_id, "assistant", stat_response)
            return {"answer": stat_response, "sources": [], "structured_events": [], "message_id": message_id}

        # Cache check
        if self.cache:
            cached = self.cache.get(question, session_id)
            if cached: return cached

        memory = self._get_memory(session_id)
        chat_history = memory.load_memory_variables({})["chat_history"]

        try:
            result = self.rag_chain.invoke({
                "input": question,
                "chat_history": chat_history,
                "language": language
            })
            if isinstance(result["answer"], dict):
                answer_text = result["answer"].get("answer_text", "")
                structured_events = result["answer"].get("events", [])
            else:
                answer_text = str(result["answer"])
                structured_events = []

            # Sanitize answer to prevent Unicode encoding errors
            answer_text = sanitize_text_for_encoding(answer_text)
        except Exception as e:
            logger.error(f"Chain failed: {e}", exc_info=True)
            answer_text = "I encountered an error."
            structured_events = []
            result = {"context": []}

        memory.chat_memory.add_message(HumanMessage(content=question))
        memory.chat_memory.add_message(AIMessage(content=answer_text))

        # Save to persistent storage and get message_id
        self.chat_storage.add_chat_message(session_id, "user", question)
        message_id = self.chat_storage.add_chat_message(session_id, "assistant", answer_text)

        # Extract complete source metadata
        sources = []
        for d in result.get("context", []):
            meta = d.metadata
            sources.append({
                "event_id": meta.get("event_id"),
                "title": meta.get("title"),
                "city": meta.get("city"),
                "category": meta.get("category"),
                "date": meta.get("start_date"),
                "score": meta.get("score", 0.0),
                "match_type": meta.get("match_type", "Unknown")
            })

        # Add retrieval stats
        retrieval_stats = result.get("retrieved_data", {})

        res = {
            "answer": answer_text,
            "structured_events": structured_events,
            "message_id": message_id,
            "sources": sources,
            "retrieval_stats": {
                "total_count": retrieval_stats.get("actual_k", len(sources)),
                "exact_count": sum(1 for s in sources if s.get("match_type") == "Exact Match")
            }
        }
        if self.cache: self.cache.set(question, session_id, res)
        return res
