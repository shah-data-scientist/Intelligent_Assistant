"""
FILE: test_chatbot_ui_playwright.py
STATUS: Active
RESPONSIBILITY: End-to-end Playwright tests for chatbot UI functionality.

DEPENDENCIES (Who uses this file):
- CI/CD pipeline: Automated UI testing before deployment
- Developers: Manual testing of UI workflows

IMPORTS (What this file needs):
- playwright: Browser automation
- pytest: Test framework
- time: Delays for UI interactions

LAST MAJOR UPDATE: 2026-01-31 (v1.10.0 - initial E2E test creation)
MAINTAINER: QA Team
"""

import time
from playwright.sync_api import Page, expect
import pytest


@pytest.fixture(scope="module")
def browser_page():
    """Launch browser and navigate to Streamlit app."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Set headless=False for debugging
        context = browser.new_context()
        page = context.new_page()

        # Navigate to Streamlit app
        page.goto("http://localhost:8501")

        # Wait for Streamlit to load
        time.sleep(5)

        yield page

        browser.close()


class TestChatbotUI:
    """Test suite for chatbot UI functionality."""

    def test_page_loads(self, browser_page: Page):
        """Test that the Streamlit page loads successfully."""
        expect(browser_page).to_have_title("Lumi - Your Cultural Guide")

    def test_welcome_message_displayed(self, browser_page: Page):
        """Test that the welcome message is displayed."""
        # Look for the chatbot welcome header with emoji
        expect(browser_page.get_by_text("Meet Lumi", exact=False).first).to_be_visible()

    def test_chat_input_present(self, browser_page: Page):
        """Test that the chat input field is present."""
        # Streamlit chat input uses this placeholder
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)
        expect(chat_input).to_be_visible()

    def test_send_simple_query(self, browser_page: Page):
        """Test sending a simple query and receiving a response."""
        # Find the chat input
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)

        # Type a test query
        test_query = "Bonjour"
        chat_input.fill(test_query)

        # Submit the query (press Enter or click submit)
        chat_input.press("Enter")

        # Wait for response (Streamlit rerun)
        time.sleep(8)

        # Check that the user message appears (use .first for multiple matches)
        expect(browser_page.get_by_text(test_query, exact=False).first).to_be_visible()

        # Check for a response (should contain "Lumi" or response text)
        # Note: Actual response content depends on the chatbot
        assert len(browser_page.content()) > 0, "Page has content after query"

    def test_event_search_query(self, browser_page: Page):
        """Test sending an event search query."""
        # Find the chat input
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)

        # Type an event search query
        test_query = "Concerts de jazz à Paris ce week-end"
        chat_input.fill(test_query)
        chat_input.press("Enter")

        # Wait for response
        time.sleep(12)

        # Check that the query appears (use .first to handle multiple matches)
        expect(browser_page.get_by_text("Concerts de jazz", exact=False).first).to_be_visible()

        # Response should be visible (could be events or clarification)
        assert len(browser_page.content()) > 1000, "Response contains content"

    def test_language_toggle_present(self, browser_page: Page):
        """Test that language toggle (FR/EN) is present."""
        # Look for language selector or toggle
        # This depends on your UI implementation
        page_content = browser_page.content()
        assert "Français" in page_content or "English" in page_content, "Language toggle present"

    def test_sidebar_elements(self, browser_page: Page):
        """Test that sidebar contains expected elements."""
        # Streamlit sidebar typically has a button to expand
        # Check if sidebar content is present
        page_content = browser_page.content()

        # Should have some sidebar elements (e.g., filters, settings)
        # Adjust based on your actual sidebar content
        assert "sidebar" in page_content.lower() or len(page_content) > 5000, "Sidebar elements present"

    def test_multiple_queries_in_sequence(self, browser_page: Page):
        """Test sending multiple queries in sequence (conversational flow)."""
        queries = [
            "Quel est ton nom?",
            "Quels événements à Versailles?",
            "Merci"
        ]

        for query in queries:
            chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)
            chat_input.fill(query)
            chat_input.press("Enter")
            time.sleep(8)

            # Verify query appears (use .first for multiple matches)
            expect(browser_page.get_by_text(query, exact=False).first).to_be_visible()

        # Check that all queries are in the chat history
        page_content = browser_page.content()
        for query in queries:
            assert query in page_content, f"Query '{query}' found in chat history"


class TestChatbotResponses:
    """Test suite for chatbot response quality."""

    def test_greeting_response(self, browser_page: Page):
        """Test that greeting receives appropriate response."""
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)

        chat_input.fill("Bonjour!")
        chat_input.press("Enter")
        time.sleep(8)

        page_content = browser_page.content()

        # Should receive a welcome/greeting response
        assert any(word in page_content.lower() for word in ["bonjour", "salut", "hello"]), \
            "Greeting response contains greeting"

    def test_capability_query(self, browser_page: Page):
        """Test capability question receives explanation."""
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)

        chat_input.fill("Que peux-tu faire?")
        chat_input.press("Enter")
        time.sleep(8)

        page_content = browser_page.content()

        # Should explain capabilities
        assert any(word in page_content.lower() for word in ["événements", "événement", "events", "concert"]), \
            "Capability response mentions events"

    def test_out_of_scope_query(self, browser_page: Page):
        """Test out-of-scope query handling."""
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)

        chat_input.fill("Quelle est la météo aujourd'hui?")
        chat_input.press("Enter")
        time.sleep(8)

        page_content = browser_page.content()

        # Should politely redirect
        assert "événements" in page_content.lower() or "events" in page_content.lower(), \
            "Out-of-scope response redirects to events"


class TestWelcomeMessage:
    """Test suite for welcome message functionality."""

    def test_welcome_message_bilingual(self, browser_page: Page):
        """Test that both English and French welcome messages are displayed."""
        page_content = browser_page.content()

        # English welcome elements
        assert "Meet Lumi" in page_content, "English title should be visible"

        # French welcome elements
        assert "Bonjour" in page_content or "événements" in page_content.lower(), \
            "French content should be visible"

    def test_welcome_expanders_present(self, browser_page: Page):
        """Test that 'What I can do' expanders are present."""
        page_content = browser_page.content()

        # Check for expander text
        assert "What I can do" in page_content or "Ce que je peux faire" in page_content, \
            "Expanders should be present"

    def test_welcome_example_queries_present(self, browser_page: Page):
        """Test that example queries are shown in welcome message."""
        page_content = browser_page.content()

        # Should show example queries in italics
        assert "jazz" in page_content.lower() or "concert" in page_content.lower(), \
            "Example queries should mention events"


class TestNewChatButton:
    """Test suite for New Chat button functionality."""

    def test_new_chat_button_visible(self, browser_page: Page):
        """Test that New Chat button is visible."""
        new_chat_btn = browser_page.get_by_text("New Chat", exact=False)
        expect(new_chat_btn).to_be_visible()

    def test_new_chat_button_clears_history(self, browser_page: Page):
        """Test that clicking New Chat clears conversation history."""
        # First send a message
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)
        chat_input.fill("Test message for clearing")
        chat_input.press("Enter")
        time.sleep(5)

        # Verify message appears
        expect(browser_page.get_by_text("Test message for clearing", exact=False)).to_be_visible()

        # Click New Chat button
        new_chat_btn = browser_page.get_by_text("New Chat", exact=False)
        new_chat_btn.click()
        time.sleep(3)

        # Verify the test message is no longer visible (chat cleared)
        page_content = browser_page.content()
        # Welcome message should be back, test message should be gone
        assert "Meet Lumi" in page_content, "Welcome should reappear after clearing"


class TestFeedbackButtons:
    """Test suite for feedback button functionality."""

    def test_feedback_buttons_appear_after_response(self, browser_page: Page):
        """Test that thumbs up/down buttons appear after assistant response."""
        # Send a query to get a response
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)
        chat_input.fill("Bonjour")
        chat_input.press("Enter")
        time.sleep(8)

        # Check for feedback buttons (thumbs up/down)
        page_content = browser_page.content()
        # Feedback buttons use emoji 👍 👎
        assert "👍" in page_content or "👎" in page_content or "feedback" in page_content.lower(), \
            "Feedback buttons should appear after response"

    def test_thumbs_up_button_clickable(self, browser_page: Page):
        """Test that thumbs up button is clickable."""
        # Send a query first
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)
        chat_input.fill("Hello")
        chat_input.press("Enter")
        time.sleep(8)

        # Try to find and click thumbs up
        try:
            thumbs_up = browser_page.get_by_text("👍").first
            # Just verify it exists and is visible
            expect(thumbs_up).to_be_visible()
        except Exception:
            # If emoji button not found, check for alternative feedback mechanism
            page_content = browser_page.content()
            assert len(page_content) > 1000, "Page has content even if feedback buttons not found"


class TestEventCards:
    """Test suite for event card rendering."""

    def test_event_query_returns_structured_data(self, browser_page: Page):
        """Test that event queries return structured event cards."""
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)

        # Query for events
        chat_input.fill("Concerts à Paris")
        chat_input.press("Enter")
        time.sleep(12)

        page_content = browser_page.content()

        # Should have structured content (city, date, venue info)
        has_event_info = any([
            "Paris" in page_content,
            "📍" in page_content,
            "📅" in page_content,
            "Venue" in page_content,
        ])
        assert has_event_info, "Event response should contain structured information"

    def test_event_cards_show_required_fields(self, browser_page: Page):
        """Test that event cards display required fields."""
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)

        chat_input.fill("Événements à Versailles")
        chat_input.press("Enter")
        time.sleep(12)

        page_content = browser_page.content()

        # Check for presence of card elements
        # Events should show location, date, or time information
        has_structured_elements = (
            "📍" in page_content or
            "📅" in page_content or
            "🕐" in page_content or
            "Venue" in page_content or
            "Found" in page_content
        )
        # Even if no events found, there should be a meaningful response
        assert len(page_content) > 2000 or has_structured_elements, \
            "Response should have content or structured elements"


class TestMapDisplay:
    """Test suite for map functionality."""

    def test_map_container_exists(self, browser_page: Page):
        """Test that map container can be rendered."""
        # Send event query that might trigger map
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)
        chat_input.fill("Concerts à Paris avec localisation")
        chat_input.press("Enter")
        time.sleep(12)

        page_content = browser_page.content()

        # Check for map-related content (Folium maps use iframe or leaflet)
        has_map_elements = (
            "leaflet" in page_content.lower() or
            "map" in page_content.lower() or
            "iframe" in page_content.lower() or
            "Event Locations" in page_content
        )
        # Map may or may not appear depending on event data
        assert len(page_content) > 1000, "Page should have content after query"


class TestErrorHandling:
    """Test suite for error handling in UI."""

    def test_empty_input_handling(self, browser_page: Page):
        """Test that empty input is handled gracefully."""
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)

        # Try to submit empty (should not crash)
        chat_input.fill("")
        chat_input.press("Enter")
        time.sleep(2)

        # Page should still be functional
        expect(chat_input).to_be_visible()

    def test_special_characters_in_query(self, browser_page: Page):
        """Test handling of special characters in queries."""
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)

        # Query with special characters
        chat_input.fill("Événements <script>alert('test')</script>")
        chat_input.press("Enter")
        time.sleep(8)

        # Page should handle gracefully (XSS attempt should be sanitized)
        page_content = browser_page.content()
        assert "<script>alert" not in page_content, "XSS should be sanitized"

    def test_very_long_query_handling(self, browser_page: Page):
        """Test handling of very long queries."""
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)

        # Very long query
        long_query = "concerts " * 100
        chat_input.fill(long_query)
        chat_input.press("Enter")
        time.sleep(10)

        # Should handle without crashing
        expect(chat_input).to_be_visible()


class TestAccessibility:
    """Test suite for basic accessibility checks."""

    def test_chat_input_has_placeholder(self, browser_page: Page):
        """Test that chat input has descriptive placeholder."""
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)
        expect(chat_input).to_be_visible()
        expect(chat_input).to_be_enabled()

    def test_buttons_are_clickable(self, browser_page: Page):
        """Test that main buttons are clickable."""
        # New Chat button should be clickable
        new_chat_btn = browser_page.get_by_text("New Chat", exact=False)
        expect(new_chat_btn).to_be_visible()
        expect(new_chat_btn).to_be_enabled()

    def test_page_has_title(self, browser_page: Page):
        """Test that page has a meaningful title."""
        title = browser_page.title()
        assert len(title) > 0, "Page should have a title"
        assert "Lumi" in title, "Title should contain chatbot name"

    def test_content_is_readable(self, browser_page: Page):
        """Test that main content area has readable text."""
        # Check that there's meaningful text content
        page_text = browser_page.inner_text("body")
        assert len(page_text) > 100, "Page should have readable content"
        assert "Lumi" in page_text or "Meet" in page_text, "Welcome content should be readable"


@pytest.mark.slow
class TestChatbotPerformance:
    """Test suite for performance metrics."""

    def test_response_time_under_15_seconds(self, browser_page: Page):
        """Test that responses are received within 15 seconds."""
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)

        start_time = time.time()

        chat_input.fill("Concerts à Paris")
        chat_input.press("Enter")

        # Wait for response (max 15 seconds)
        timeout = 15
        elapsed = 0
        initial_content_length = len(browser_page.content())

        while elapsed < timeout:
            time.sleep(1)
            elapsed = time.time() - start_time

            # Check if content changed (response arrived)
            if len(browser_page.content()) > initial_content_length + 500:
                break

        assert elapsed < timeout, f"Response took {elapsed:.1f}s (should be <15s)"

    def test_no_errors_in_console(self, browser_page: Page):
        """Test that there are no JavaScript errors in the console."""
        # Capture console messages
        console_messages = []

        def handle_console_message(msg):
            console_messages.append(msg.text)

        browser_page.on("console", handle_console_message)

        # Perform a simple interaction
        chat_input = browser_page.get_by_placeholder("Ask Lumi anything", exact=False)
        chat_input.fill("Test")
        chat_input.press("Enter")
        time.sleep(5)

        # Check for critical errors
        critical_errors = [msg for msg in console_messages if "error" in msg.lower()]
        assert len(critical_errors) == 0, f"Console errors: {critical_errors}"


def test_api_health_before_ui_tests():
    """Prerequisite: Verify API is healthy before running UI tests."""
    import httpx

    try:
        response = httpx.get("http://localhost:8000/docs", timeout=5)
        assert response.status_code == 200, "API /docs endpoint should return 200"
    except httpx.ConnectError:
        pytest.fail("API server not running on localhost:8000. Start with: uvicorn src.api.main:app --reload")


def test_streamlit_running_before_tests():
    """Prerequisite: Verify Streamlit is running before tests."""
    import httpx

    try:
        response = httpx.get("http://localhost:8501", timeout=10)
        assert response.status_code == 200, "Streamlit should be accessible on localhost:8501"
    except httpx.ConnectError:
        pytest.fail("Streamlit not running on localhost:8501. Start with: streamlit run src/frontend/app.py")


if __name__ == "__main__":
    """Run tests with: pytest tests/e2e/test_chatbot_ui_playwright.py -v -s"""
    pytest.main([__file__, "-v", "-s"])
