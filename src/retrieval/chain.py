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
from src.generation.prompts import get_rag_prompt, get_contextualize_q_prompt, get_metadata_extraction_prompt
from src.retrieval.retriever import EventRetriever
from src.data.chat_history import SQLiteChatMessageHistory
from src.data.storage import EventStorage
from src.security.guardrails import check_safety

logger = logging.getLogger(__name__)

def get_session_history(session_id: str, storage: EventStorage | None = None) -> BaseChatMessageHistory:
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
    ) -> None:
        """Initialize the RAG chain.

        Args:
            vector_store: EventVectorStore instance
            llm: MistralLLM instance
            k: Number of events to retrieve
            chain: Optional pre-configured conversational chain (for testing)
            history_factory: Optional factory for chat history (for testing)
        """
        self.vector_store = vector_store or EventVectorStore()
        try:
            self.vector_store.load_index()
        except Exception as e:
            logger.warning(f"Could not load FAISS index: {e}. Build it first if needed.")

        self.llm = llm or MistralLLM()
        
        # Metadata Extraction Chain
        extraction_prompt = get_metadata_extraction_prompt()
        self.extraction_chain = extraction_prompt | self.llm.llm | JsonOutputParser()

        # Use provided history factory or default
        session_history_factory = history_factory or (lambda sid: get_session_history(sid, self.vector_store.storage))
        
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
                # Extract filters (using the raw query for extraction is often better than the reformulated one for dates)
                # But here we only have input_query which is the reformulated one. That's fine.
                filters = self.extraction_chain.invoke({"question": input_query})
                logger.info(f"Extracted filters: {filters}")
                
                # Clean filters (remove nulls)
                clean_filters = {k: v for k, v in filters.items() if v}
                
                # Perform search
                results = self.vector_store.search(input_query, k=k, metadata_filter=clean_filters)
                
                # Convert to documents (manually, since we bypassed retriever)
                docs = []
                for event, score in results:
                    # We reuse the logic from EventRetriever or reimplement it briefly
                    content = event.to_text()
                    meta = event.get_metadata()
                    meta["score"] = score
                    # Add lat/lon from schema requirements
                    if event.location and event.location.coordinates:
                        meta["latitude"] = event.location.coordinates.get("lat")
                        meta["longitude"] = event.location.coordinates.get("lon")
                    
                    from langchain_core.documents import Document
                    docs.append(Document(page_content=content, metadata=meta))
                
                return docs
            except Exception as e:
                logger.error(f"Hybrid retrieval failed: {e}")
                # Fallback to simple retrieval
                return self.retriever.invoke(input_query)

        # 3. QA Chain
        qa_prompt = get_rag_prompt()
        
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        # Main Chain logic:
        
        context_retrieval_chain = (
            history_aware_retriever | retrieve_docs_hybrid
        )

        self.rag_chain = (
            RunnablePassthrough.assign(
                context=context_retrieval_chain
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
        self.conversational_chain = RunnableWithMessageHistory(
            self.rag_chain,
            get_session_history,
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
        
        result = self.conversational_chain.invoke(
            {"input": question},
            config={"configurable": {"session_id": session_id}},
        )
        
        answer = result["answer"]
        docs = result.get("context", [])

        # Retrieve the ID of the assistant's message we just saved
        message_id = None
        try:
            with self.vector_store.storage.SessionLocal() as session:
                from src.data.storage import ConversationRecord
                from sqlalchemy import select
                stmt = select(ConversationRecord.id).where(
                    ConversationRecord.session_id == session_id,
                    ConversationRecord.role == "assistant"
                ).order_by(ConversationRecord.timestamp.desc()).limit(1)
                message_id = session.execute(stmt).scalar()
        except Exception as e:
            logger.error(f"Failed to retrieve message_id for feedback: {e}")
        
        return {
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
                    "longitude": d.metadata.get("longitude")
                }
                for d in docs
            ]
        }


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