"""RAG orchestration chain for cultural events with history."""

import logging
from typing import Any, Dict

from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableBranch
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.chat_history import BaseChatMessageHistory

# Removing langchain.chains imports to rely on core LCEL
# from langchain.chains import create_history_aware_retriever, create_retrieval_chain
# from langchain.chains.combine_documents import create_stuff_documents_chain

from src.models.vector_store import EventVectorStore
from src.generation.llm import MistralLLM
from src.generation.prompts import get_rag_prompt, get_contextualize_q_prompt, get_metadata_extraction_prompt, get_query_refinement_prompt
from src.retrieval.retriever import EventRetriever
from src.retrieval.cache import QueryCache
from src.data.chat_history import SQLiteChatMessageHistory
from src.data.storage import EventStorage
from src.data.chat_storage import ChatStorage
from src.security.guardrails import check_safety

logger = logging.getLogger(__name__)

def get_session_history(session_id: str, storage: ChatStorage | None = None) -> BaseChatMessageHistory:
    """Get persistent chat history for a session."""
    return SQLiteChatMessageHistory(session_id=session_id, storage=storage)


class RAGChain:
    """Orchestrator for the Cultural Events RAG system with History."""

    def __init__(
        self,
        vector_store: EventVectorStore | None = None,
        llm: MistralLLM | None = None,
        k: int = 5,
        chain: Any | None = None,
        history_factory: Any | None = None,
        chat_storage: ChatStorage | None = None,
        enable_cache: bool = True,
        cache_ttl_minutes: int = 60,
    ) -> None:
        """Initialize the RAG chain.

        Args:
            vector_store: EventVectorStore instance
            llm: MistralLLM instance
            k: Number of events to retrieve
            chain: Optional pre-configured conversational chain (for testing)
            history_factory: Optional factory for chat history (for testing)
            chat_storage: Optional ChatStorage instance
            enable_cache: Enable query result caching (default: True)
            cache_ttl_minutes: Cache time-to-live in minutes (default: 60)
        """
        self.vector_store = vector_store or EventVectorStore()
        try:
            self.vector_store.load_index()
        except Exception as e:
            logger.warning(f"Could not load FAISS index: {e}. Build it first if needed.")

        self.llm = llm or MistralLLM()
        self.chat_storage = chat_storage or ChatStorage()

        # Initialize cache if enabled
        self.cache = QueryCache(ttl_minutes=cache_ttl_minutes) if enable_cache else None
        if self.cache:
            logger.info(f"Query caching ENABLED (TTL: {cache_ttl_minutes}min)")
        
        # Metadata Extraction Chain
        extraction_prompt = get_metadata_extraction_prompt()
        self.extraction_chain = extraction_prompt | self.llm.llm | JsonOutputParser()

        # Query Refinement Chain
        refinement_prompt = get_query_refinement_prompt()
        self.refinement_chain = refinement_prompt | self.llm.llm | StrOutputParser()

        # Use provided history factory or default
        session_history_factory = history_factory or (lambda sid: get_session_history(sid, self.chat_storage))
        
        if chain:
            # If a chain is provided (mock), wrap it with history
            self.conversational_chain = RunnableWithMessageHistory(
                chain,
                session_history_factory,
                input_messages_key="input",
                history_messages_key="chat_history",
                output_messages_key="answer", 
            )
            logger.info("RAGChain initialized with injected chain.")
            return

        self.retriever = EventRetriever(vector_store=self.vector_store, k=k)
        
        # --- Pure LCEL Implementation ---

        # 1. History-Aware Question Reformulation
        # Optimize: If history is empty, pass input directly. Else, reformulate.
        contextualize_q_prompt = get_contextualize_q_prompt()
        
        reformulation_chain = (
            contextualize_q_prompt
            | self.llm.llm
            | StrOutputParser()
        )
        
        history_aware_retriever = RunnableBranch(
            (
                lambda x: not x.get("chat_history", []),
                RunnableLambda(lambda x: x["input"])
            ),
            reformulation_chain
        )

        # 2. Hybrid Retrieval Branch (Semantic + Filters)
        # We define a custom function to handle extraction + search
        def retrieve_docs_hybrid(input_query: str):
            try:
                # Refine query (typos/expansion)
                refined_query = self.refinement_chain.invoke({"question": input_query})
                logger.info(f"Refined query: '{input_query}' -> '{refined_query}'")

                # Extract filters (using the refined query)
                filters = self.extraction_chain.invoke({"question": refined_query})
                logger.info(f"Extracted filters: {filters}")
                
                # Clean filters (remove nulls)
                clean_filters = {k: v for k, v in filters.items() if v}
                
                # Perform search with refined query
                results = self.vector_store.search(refined_query, k=k, metadata_filter=clean_filters)
                
                # Fallback Logic: If no results and city filter exists, try removing city (regional search)
                fallback_triggered = False
                original_city = clean_filters.get("city")
                
                if not results and original_city:
                    logger.info(f"No results for {original_city}, attempting fallback to regional search.")
                    fallback_filters = clean_filters.copy()
                    del fallback_filters["city"]
                    results = self.vector_store.search(refined_query, k=k, metadata_filter=fallback_filters)
                    if results:
                        fallback_triggered = True

                # Convert to documents (manually, since we bypassed retriever)
                docs = []
                from langchain_core.documents import Document

                # NOTE: Removed SYSTEM_NOTE injection - it was causing confusing answers
                # The retrieval system finds relevant events, and the LLM can present them naturally
                # without disclaimers about fallback searches

                for event, score in results:
                    # We reuse the logic from EventRetriever or reimplement it briefly
                    content = event.to_text()
                    meta = event.get_metadata()
                    meta["score"] = score
                    # Add lat/lon from schema requirements
                    if event.location and event.location.coordinates:
                        meta["latitude"] = event.location.coordinates.get("lat")
                        meta["longitude"] = event.location.coordinates.get("lon")
                    
                    docs.append(Document(page_content=content, metadata=meta))
                
                return docs
            except Exception as e:
                logger.error(f"Hybrid retrieval failed: {e}")
                # Fallback to simple retrieval
                return self.retriever.invoke(input_query)

        # 3. QA Chain
        qa_prompt = get_rag_prompt()
        
        # Pre-fetch global stats
        try:
            total_events = self.vector_store.storage.count_events()
            min_date, max_date = self.vector_store.storage.get_date_range()
            date_range_str = f"{min_date.strftime('%Y-%m-%d') if min_date else '?'} to {max_date.strftime('%Y-%m-%d') if max_date else '?'}"
        except Exception as e:
            logger.warning(f"Could not fetch global stats: {e}")
            total_events = "Unknown"
            date_range_str = "Unknown"

        def format_docs(docs):
            """Format documents with source attribution and metadata for citation."""
            seen_event_ids = set()
            formatted_docs = []
            source_num = 1  # Track actual source numbering after deduplication

            for doc in docs:
                # Extract metadata
                meta = doc.metadata
                event_id = meta.get("event_id", "unknown")

                # Deduplicate by event_id to avoid showing same event multiple times
                if event_id != "unknown" and event_id in seen_event_ids:
                    continue

                seen_event_ids.add(event_id)
                relevance_score = meta.get("score", 0.0)

                # Add source header for LLM citation
                source_header = f"=== SOURCE {source_num} (Event ID: {event_id}, Relevance: {relevance_score:.2f}) ==="

                formatted_docs.append(f"{source_header}\n{doc.page_content}")
                source_num += 1

            if formatted_docs:
                return "\n\n" + "\n\n".join(formatted_docs) + "\n\n"
            return ""

        # Main Chain logic:
        
        context_retrieval_chain = (
            history_aware_retriever | retrieve_docs_hybrid
        )

        self.rag_chain = (
            RunnablePassthrough.assign(
                context=context_retrieval_chain,
                total_events=lambda _: str(total_events),
                date_range=lambda _: date_range_str,
                k=lambda _: str(k)
            )
            .assign(
                answer=(
                    RunnablePassthrough.assign(
                        context=lambda x: format_docs(x["context"])
                    )
                    | qa_prompt
                    | self.llm.llm
                    | StrOutputParser()
                )
            )
        )
        
        # 4. Wrap with Message History
        # Use lambda to pass shared storage instance to avoid creating new connections
        self.conversational_chain = RunnableWithMessageHistory(
            self.rag_chain,
            lambda sid: get_session_history(sid, self.chat_storage),
            input_messages_key="input",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )
        
        logger.info("RAGChain with history initialized successfully")

    def query(self, question: str, session_id: str = "default_session") -> str:
        """Process a user question with history.

        Args:
            question: User's natural language question
            session_id: Session identifier for chat history

        Returns:
            Generated response string
        """
        logger.info(f"Processing query: {question} (session: {session_id})")
        check_safety(question)
        
        result = self.conversational_chain.invoke(
            {"input": question},
            config={"configurable": {"session_id": session_id}},
        )
        return result["answer"]

    def stream_query(self, question: str, session_id: str = "default_session"):
        """Stream the response chunk by chunk.

        Args:
            question: User question
            session_id: Session identifier

        Yields:
            Response chunks
        """
        logger.info(f"Streaming query: {question} (session: {session_id})")
        check_safety(question)
        
        # We need to stream the 'answer' key.
        # RunnableWithMessageHistory.stream yields dicts usually if output_keys are involved,
        # or we might need to pick_stream.
        
        # Simple approach: iterate over the stream
        for chunk in self.conversational_chain.stream(
            {"input": question},
            config={"configurable": {"session_id": session_id}},
        ):
            # chunk is likely a dict {'answer': 'chunk'} or just 'chunk' depending on configuration
            if isinstance(chunk, dict) and "answer" in chunk:
                yield chunk["answer"]
            elif isinstance(chunk, str):
                yield chunk
            # If using LCEL with dict output, it might stream dict updates.

    def query_with_metadata(self, question: str, session_id: str = "default_session") -> Dict[str, Any]:
        """Process query and return response with source documents.

        Args:
            question: User's natural language question
            session_id: Session identifier

        Returns:
            Dictionary with 'answer', 'sources', and 'message_id'
        """
        logger.info(f"Processing query with metadata: {question} (session: {session_id})")
        check_safety(question)

        # Detect follow-up queries (references to previous context)
        follow_up_keywords = ['first', 'second', 'third', 'last', 'previous', 'that one', 'this one',
                              'tell me more', 'more about', 'more info', 'premier', 'deuxi', 'troisi',
                              'dernier', 'celui', 'cette', 'plus sur', 'davantage']
        is_follow_up = any(keyword in question.lower() for keyword in follow_up_keywords)

        # Check cache (skip for follow-up queries that reference previous context)
        if self.cache and not is_follow_up:
            cached_result = self.cache.get(question, session_id)
            if cached_result:
                logger.info("Returning cached result")
                return cached_result

        # Process query (cache miss or cache disabled)
        result = self.conversational_chain.invoke(
            {"input": question},
            config={"configurable": {"session_id": session_id}},
        )

        answer = result["answer"]
        docs = result.get("context", [])

        # Retrieve the ID of the assistant's message we just saved
        message_id = None
        try:
            with self.chat_storage.SessionLocal() as session:
                from src.data.chat_storage import ConversationRecord
                from sqlalchemy import select
                stmt = select(ConversationRecord.id).where(
                    ConversationRecord.session_id == session_id,
                    ConversationRecord.role == "assistant"
                ).order_by(ConversationRecord.timestamp.desc()).limit(1)
                message_id = session.execute(stmt).scalar()
        except Exception as e:
            logger.error(f"Failed to retrieve message_id for feedback: {e}")

        # Build result
        result_dict = {
            "answer": answer,
            "message_id": message_id,
            "sources": [
                {
                    "title": d.metadata.get("title"),
                    "city": d.metadata.get("city"),
                    "date": d.metadata.get("start_date"),
                    "url": d.metadata.get("url"),
                    "score": d.metadata.get("score"),
                    "latitude": d.metadata.get("latitude"),
                    "longitude": d.metadata.get("longitude"),
                    "full_text": d.page_content  # Add full event details for faithfulness evaluation
                }
                for d in docs
            ]
        }

        # Cache result (skip follow-up queries that reference previous context)
        if self.cache and not is_follow_up:
            self.cache.set(question, session_id, result_dict)

        return result_dict


def main() -> None:
    """CLI entry point for testing the RAG system with history."""
    logging.basicConfig(level=logging.INFO)
    
    chain = RAGChain()
    session_id = "test_user_1"
    
    print("\n--- Interaction 1 ---")
    q1 = "Are there any jazz concerts in Paris?"
    print(f"User: {q1}")
    result1 = chain.query_with_metadata(q1, session_id)
    print(f"AI: {result1['answer']}")
    
    print("\n--- Interaction 2 (Follow-up) ---")
    q2 = "What is the address of the first one?"
    print(f"User: {q2}")
    result2 = chain.query_with_metadata(q2, session_id)
    print(f"AI: {result2['answer']}")


if __name__ == "__main__":
    main()