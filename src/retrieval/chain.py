"""RAG orchestration chain for cultural events with history."""

import logging
from typing import Any, Dict

from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.chat_history import BaseChatMessageHistory, InMemoryChatMessageHistory
# Removing langchain.chains imports to rely on core LCEL
# from langchain.chains import create_history_aware_retriever, create_retrieval_chain
# from langchain.chains.combine_documents import create_stuff_documents_chain

from src.models.vector_store import EventVectorStore
from src.generation.llm import MistralLLM
from src.generation.prompts import get_rag_prompt, get_contextualize_q_prompt
from src.retrieval.retriever import EventRetriever

logger = logging.getLogger(__name__)

# Global store for chat histories (POC only - use Redis/SQL for production)
store: Dict[str, BaseChatMessageHistory] = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    """Get or create chat history for a session."""
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]


class RAGChain:
    """Orchestrator for the Cultural Events RAG system with History."""

    def __init__(
        self,
        vector_store: EventVectorStore | None = None,
        llm: MistralLLM | None = None,
        k: int = 5,
        chain: Any | None = None,
    ) -> None:
        """Initialize the RAG chain.

        Args:
            vector_store: EventVectorStore instance
            llm: MistralLLM instance
            k: Number of events to retrieve
            chain: Optional pre-configured conversational chain (for testing)
        """
        self.vector_store = vector_store or EventVectorStore()
        try:
            self.vector_store.load_index()
        except Exception as e:
            logger.warning(f"Could not load FAISS index: {e}. Build it first if needed.")

        self.llm = llm or MistralLLM()
        
        if chain:
            self.conversational_chain = chain
            logger.info("RAGChain initialized with injected chain.")
            return

        self.retriever = EventRetriever(vector_store=self.vector_store, k=k)
        
        # --- Pure LCEL Implementation ---

        # 1. History-Aware Question Reformulation
        # If history exists, reformulate the question. Otherwise, use the original.
        contextualize_q_prompt = get_contextualize_q_prompt()
        
        history_aware_retriever = (
            RunnablePassthrough.assign(
                chat_history=lambda x: x.get("chat_history", [])
            )
            | contextualize_q_prompt
            | self.llm.llm
            | StrOutputParser()
        )

        # 2. Retrieval Branch
        # We need a branch that takes the reformulated question (str) and retrieves docs
        def retrieve_docs(input_query: str):
            return self.retriever.invoke(input_query)

        # 3. QA Chain
        qa_prompt = get_rag_prompt()
        
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        # Main Chain logic:
        # Input: {"input": "question", "chat_history": [...]}
        # Step A: Reformulate question -> "standalone_question"
        # Step B: Retrieve docs using "standalone_question" -> "context"
        # Step C: Answer using "context" and "input" (or "standalone_question"?)
        
        context_retrieval_chain = (
            history_aware_retriever | retrieve_docs
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
            Dictionary with 'answer' and 'sources'
        """
        logger.info(f"Processing query with metadata: {question} (session: {session_id})")
        
        result = self.conversational_chain.invoke(
            {"input": question},
            config={"configurable": {"session_id": session_id}},
        )
        
        answer = result["answer"]
        docs = result.get("context", [])
        
        return {
            "answer": answer,
            "sources": [
                {
                    "title": d.metadata.get("title"),
                    "city": d.metadata.get("city"),
                    "date": d.metadata.get("start_date"),
                    "url": d.metadata.get("url"),
                    "score": d.metadata.get("score")
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