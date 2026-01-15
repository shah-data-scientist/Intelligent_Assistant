"""RAG orchestration chain for cultural events."""

import logging
from typing import Any, Dict, List

from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

from src.models.vector_store import EventVectorStore
from src.generation.llm import MistralLLM
from src.generation.prompts import get_rag_prompt
from src.retrieval.retriever import EventRetriever

logger = logging.getLogger(__name__)


class RAGChain:
    """Orchestrator for the Cultural Events RAG system."""

    def __init__(
        self,
        vector_store: EventVectorStore | None = None,
        llm: MistralLLM | None = None,
        k: int = 5,
    ) -> None:
        """Initialize the RAG chain.

        Args:
            vector_store: EventVectorStore instance
            llm: MistralLLM instance
            k: Number of events to retrieve
        """
        self.vector_store = vector_store or EventVectorStore()
        # Ensure index is loaded
        try:
            self.vector_store.load_index()
        except Exception as e:
            logger.warning(f"Could not load FAISS index: {e}. Build it first if needed.")

        self.llm = llm or MistralLLM()
        self.retriever = EventRetriever(vector_store=self.vector_store, k=k)
        self.prompt = get_rag_prompt()
        
        # Build the chain using LCEL
        self.chain = (
            RunnableParallel({
                "context": self.retriever,
                "question": RunnablePassthrough()
            })
            | self.prompt
            | self.llm.llm  # Access the underlying ChatMistralAI instance
            | StrOutputParser()
        )
        
        logger.info("RAGChain initialized successfully")

    def query(self, question: str) -> str:
        """Process a user question and generate a response.

        Args:
            question: User's natural language question

        Returns:
            Generated response string
        """
        logger.info(f"Processing query: {question}")
        return self.chain.invoke(question)

    async def aquery(self, question: str) -> str:
        """Process a user question asynchronously.

        Args:
            question: User's natural language question

        Returns:
            Generated response string
        """
        logger.info(f"Processing async query: {question}")
        return await self.chain.ainvoke(question)

    def query_with_metadata(self, question: str) -> Dict[str, Any]:
        """Process query and return both response and source documents.

        Args:
            question: User's natural language question

        Returns:
            Dictionary with 'answer' and 'sources'
        """
        logger.info(f"Processing query with metadata: {question}")
        
        # Retrieve docs manually using invoke
        docs = self.retriever.invoke(question)
        
        # Generate answer using the chain
        answer = self.chain.invoke(question)
        
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
    """CLI entry point for testing the RAG system."""
    logging.basicConfig(level=logging.INFO)
    
    chain = RAGChain()
    
    questions = [
        "Quels concerts de jazz y a-t-il prochainement à Paris ?",
        "Are there any activities for children this weekend in Versailles?",
        "Je cherche une pièce de théâtre moderne."
    ]
    
    for q in questions:
        print("\n" + "="*50)
        print(f"QUESTION: {q}")
        print("="*50)
        
        result = chain.query_with_metadata(q)
        print(f"\nANSWER:\n{result['answer']}")
        
        print("\nSOURCES:")
        for i, source in enumerate(result['sources'], 1):
            print(f"{i}. {source['title']} ({source['city']}) - Score: {source['score']:.4f}")


if __name__ == "__main__":
    main()
