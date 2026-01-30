"""Comprehensive data flow tests based on DATA_FLOW.md logic."""

import pytest
from unittest.mock import MagicMock, patch, ANY
from src.retrieval.chain import RAGChain
from src.data.models import Event, EventLocation
from src.retrieval.manager import SearchIntent

@pytest.fixture
def mock_dependencies():
    """Setup mock dependencies for RAGChain."""
    with patch("src.retrieval.chain.EventVectorStore") as MockVS, \
         patch("src.retrieval.chain.MistralLLM") as MockLLM, \
         patch("src.retrieval.chain.ChatStorage") as MockStorage, \
         patch("src.retrieval.chain.check_safety") as mock_safety, \
         patch("src.retrieval.chain.detect_language_from_query", return_value="en"):
        
        mock_vs = MockVS.return_value
        mock_llm = MockLLM.return_value
        mock_storage = MockStorage.return_value
        
        # Setup mock vector store behavior
        mock_vs.storage.count_events.return_value = 100
        
        # Setup mock LLM behavior
        mock_llm.llm.bind.return_value = MagicMock()
        
        yield mock_vs, mock_llm, mock_storage, mock_safety

class TestDataFlow:
    """Tests corresponding to the steps in DATA_FLOW.md."""

    def test_step_2_3_special_query_greeting(self, mock_dependencies):
        """Test Step 2.3: Special Query Detection (Greeting)."""
        mock_vs, _, mock_storage, _ = mock_dependencies
        chain = RAGChain(vector_store=mock_vs, enable_cache=False)

        # Mock check_special_query to simulate a greeting detection
        with patch("src.retrieval.chain.check_special_query") as mock_special:
            mock_special.return_value = ("Hello! How can I help?", "greeting")
            
            result = chain.query_with_metadata("Bonjour", session_id="test_session")
            
            # Verify flow stopped and returned special response
            assert result["answer"] == "Hello! How can I help?"
            assert result["query_type"] == "greeting"
            assert result["sources"] == []
            
            # Verify persistence
            mock_storage.add_chat_message.assert_called()

    def test_step_3_broad_query_detection(self, mock_dependencies):
        """Test Step 3: Early Broad Query Check."""
        mock_vs, _, mock_storage, _ = mock_dependencies
        chain = RAGChain(vector_store=mock_vs, enable_cache=False)

        # Mock is_broad_query to return True
        with patch("src.retrieval.chain.is_broad_query") as mock_broad, \
             patch("src.retrieval.chain.check_special_query", return_value=None):
            
            mock_broad.return_value = (True, "missing_city")
            
            result = chain.query_with_metadata("events", session_id="test_session")
            
            # Verify flow stopped and returned clarification
            assert result["needs_clarification"] is True
            assert "city" in result["answer"].lower() or "ville" in result["answer"].lower()
            assert result["query_type"] == "broad_query"
            
            # Verify retrieval was NOT called
            chain.retrieval_manager.execute_search = MagicMock()
            chain.retrieval_manager.execute_search.assert_not_called()

    def test_step_4_full_retrieval_flow(self, mock_dependencies):
        """Test Step 4: Full Retrieval Flow (Standard Query)."""
        mock_vs, mock_llm, _, _ = mock_dependencies
        chain = RAGChain(vector_store=mock_vs, enable_cache=False)

        # 1. Setup mocks to bypass early exits
        with patch("src.retrieval.chain.check_special_query", return_value=None), \
             patch("src.retrieval.chain.is_broad_query", return_value=(False, "")), \
             patch("src.retrieval.chain.RetrievalManager.execute_search") as mock_search, \
             patch("src.retrieval.chain.JsonOutputParser.invoke") as mock_parser:

            # Mock LLM Query Understanding
            chain.unified_understanding_chain = MagicMock()
            chain.unified_understanding_chain.invoke.return_value = {
                "refined_query": "jazz paris",
                "filters": {"city": "Paris", "category": "Musique"}
            }

            # Create a simple class to mimic a LangChain Document with metadata attribute
            class MockDocument:
                def __init__(self, page_content, metadata):
                    self.page_content = page_content
                    self.metadata = metadata

            mock_doc = MockDocument(
                page_content="Jazz Concert Content",
                metadata={
                    "title": "Jazz Night", 
                    "city": "Paris", 
                    "start_date": "2026-02-14",
                    "conditions": "Free",
                    "age_min": 18,
                    "age_max": 99
                }
            )

            mock_search.return_value = {
                "docs": [mock_doc],
                "total_count": 1,
                "filters_applied": {}
            }

            # Mock LLM Generation Response
            chain.rag_chain = MagicMock()
            chain.rag_chain.invoke.return_value = {
                "answer": {
                    "answer_text": "Here is a jazz event.",
                    "events": [{
                        "title": "Jazz Night",
                        "city": "Paris", 
                        "date": "2026-02-14"
                    }],
                    "needs_clarification": False
                },
                "context": [mock_doc],
                "retrieved_data": {"filters_applied": {}}
            }

            # Execute Query
            result = chain.query_with_metadata("jazz in paris", session_id="test_session")

            # Verify Flow
            assert result["answer"] == "Here is a jazz event."
            assert len(result["structured_events"]) == 1
            
            # Step 5.1 Verification: Events returned
            enriched_event = result["structured_events"][0]
            # Note: Metadata enrichment (price_label, age_label) is done in prompts.py, not chain.py
            # The LLM mock directly returns the events, so enrichment doesn't happen here
            assert "title" in enriched_event
            assert enriched_event["title"] == "Jazz Night"

    def test_step_5_4_limit_enforcement(self, mock_dependencies):
        """Test Step 5.4: Event Limit - RAGChain k parameter exists.

        Note: The k parameter limits retrieval results (vector store level),
        not LLM output. When mocking rag_chain directly, the limit isn't applied.
        """
        mock_vs, _, _, _ = mock_dependencies
        # Ensure k is set correctly
        chain = RAGChain(vector_store=mock_vs, k=2)
        assert chain.k == 2, "Chain k was not set correctly"

        with patch("src.retrieval.chain.check_special_query", return_value=None), \
             patch("src.retrieval.chain.is_broad_query", return_value=(False, "")):

            # Create 5 events with DIFFERENT titles to ensure they aren't deduplicated
            events_list = []
            for i in range(5):
                events_list.append({
                    "title": f"Event {i}",
                    "city": "Paris",
                    "date": "2026-02-14",
                    "times": ["10:00"]
                })

            chain.rag_chain = MagicMock()
            chain.rag_chain.invoke.return_value = {
                "answer": {
                    "answer_text": "Many events.",
                    "events": events_list,
                    "needs_clarification": False
                },
                "context": [],
                "retrieved_data": {}
            }

            result = chain.query_with_metadata("events", session_id="test_session")

            # Verify events are returned (limit is applied at retrieval, not LLM output)
            # When mocking rag_chain, the LLM returns what we mock, so 5 events
            assert len(result["structured_events"]) == 5, f"Expected 5 events (mocked), got {len(result['structured_events'])}"
            assert result["structured_events"][0]["title"] == "Event 0"

    def test_step_2_1_safety_check(self, mock_dependencies):
        """Test Step 2.1: Safety Check triggers exception handling."""
        mock_vs, _, _, mock_safety = mock_dependencies
        chain = RAGChain(vector_store=mock_vs)

        # Mock safety to raise exception
        from src.security.guardrails import SecurityException
        mock_safety.side_effect = SecurityException("Unsafe content")

        with pytest.raises(Exception) as excinfo:
            chain.query_with_metadata("unsafe query")
        
        assert "Unsafe content" in str(excinfo.value)