"""
FILE: app.py
STATUS: Active
RESPONSIBILITY: Streamlit frontend for the Intelligent Cultural Assistant chatbot.

DEPENDENCIES (Who uses this file):
- Users: Direct interaction via web browser

IMPORTS (What this file needs):
- streamlit: UI framework
- requests: HTTP calls to API
- folium: Map rendering
- streamlit_folium: Streamlit map integration
- uuid: Session ID generation

LAST MAJOR UPDATE: 2026-02-02
MAINTAINER: Frontend Team
"""

import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import uuid
import os

# Import centralized config for chatbot identity
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.config import settings
from src.utils.i18n import get_translator

# Page configuration - Uses centralized chatbot name from config
st.set_page_config(page_title=f"{settings.chatbot_name} - Your Cultural Guide", page_icon="🎭", layout="wide")

# Constants - Read from environment variables (for Docker) or use defaults (for local dev)
API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1/chat")
API_KEY = os.getenv("API_KEY", "dev-secret-key")

# Chatbot name and personality - From centralized config
CHATBOT_NAME = settings.chatbot_name
CHATBOT_EMOJI = "🎭"


# Bilingual welcome messages - Uses i18n framework
def get_welcome_message(language: str = "fr") -> tuple[str, str]:
    """Get concise and detailed welcome messages for specified language.

    Returns:
        Tuple of (concise_message, detailed_message)
    """
    t = get_translator(language)

    # Concise message (8 lines)
    concise = f"""
{t.get("welcome.title", name=settings.chatbot_name)}

{t.get("welcome.intro")}

{t.get("welcome.try_asking")}
*{t.get("welcome.example_1")}* | *{t.get("welcome.example_2")}*

{t.get("welcome.languages")}
"""

    # Detailed message (for expander)
    detailed = f"""
{t.get("welcome.detailed_categories")}
- {t.get("welcome.category_music")}
- {t.get("welcome.category_art")}
- {t.get("welcome.category_theater")}
- {t.get("welcome.category_festivals")}

{t.get("welcome.good_to_know")}
- {t.get("welcome.database_info")}
- {t.get("welcome.nearby_info")}
"""

    return concise, detailed


# Generate welcome messages
WELCOME_EN, DETAILED_EN = get_welcome_message("en")
WELCOME_FR, DETAILED_FR = get_welcome_message("fr")

# Initialize session state for chat history and session ID
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "__WELCOME__", "is_welcome": True}]

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = set()

if "language" not in st.session_state:
    st.session_state.language = "en"

# Main UI - No sidebar, clean interface
st.title(f"{CHATBOT_EMOJI} {CHATBOT_NAME} — Your Cultural Guide")

# Header row with language selection and Start Fresh button
col1, col2, col3, col4 = st.columns([0.15, 0.15, 0.5, 0.2])
with col1:
    if st.button("🇬🇧 English", use_container_width=True, type="secondary" if st.session_state.language == "en" else "primary"):
        st.session_state.language = "en"
        st.rerun()
with col2:
    if st.button("🇫🇷 Français", use_container_width=True, type="secondary" if st.session_state.language == "fr" else "primary"):
        st.session_state.language = "fr"
        st.rerun()
with col4:
    if st.button("🔄 Start Fresh", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": "__WELCOME__", "is_welcome": True}]
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.feedback_submitted = set()
        st.rerun()

st.caption(f"Session: `{st.session_state.session_id[:8]}...` • v1.0.0")


# Function to submit feedback to API
def submit_feedback(message_id, is_positive, comment=""):
    try:
        headers = {"X-API-Key": API_KEY}
        payload = {"message_id": message_id, "is_positive": is_positive, "comment": comment}
        resp = requests.post("http://localhost:8000/api/v1/feedback", json=payload, headers=headers)
        if resp.status_code == 200:
            st.session_state.feedback_submitted.add(message_id)
            return True
    except Exception as e:
        st.error(f"Feedback error: {e}")
    return False


# Chat interface
# Display chat messages from history on app rerun
for i, message in enumerate(st.session_state.messages):
    # Special handling for welcome message - two column layout with expanders
    if message.get("is_welcome"):
        with st.chat_message("assistant", avatar="🎭"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(WELCOME_EN)
                with st.expander("📖 What I can do"):
                    st.markdown(DETAILED_EN)
            with col2:
                st.markdown(WELCOME_FR)
                with st.expander("📖 Ce que je peux faire"):
                    st.markdown(DETAILED_FR)
        continue

    with st.chat_message(message["role"], avatar="🎭" if message["role"] == "assistant" else None):
        st.markdown(message["content"])

        # STRUCTURED EVENT CARDS
        if "structured_events" in message and message["structured_events"]:
            st.divider()
            st.caption(f"Found {len(message['structured_events'])} events:")
            for event in message["structured_events"]:
                with st.container(border=True):
                    c1, c2 = st.columns([0.7, 0.3])
                    with c1:
                        st.subheader(event.get("title", "Unknown Event"))
                        st.text(f"📍 {event.get('city', 'Unknown City')} • 📅 {event.get('date', 'Unknown Date')}")
                        # Always show times and venue (required fields)
                        st.text(f"🕐 {event.get('times_display', 'Unknown')}")
                        st.caption(f"Venue: {event.get('location', 'Unknown')}")
                    with c2:
                        st.markdown(f"**{event.get('price_label', 'Unknown Price')}**")
                        st.caption(event.get("age_label", "All Ages"))
                        if event.get("url"):
                            st.link_button("More Info", event["url"])

        # Fallback to old sources if no structured events but sources exist
        elif "sources" in message and message["sources"]:
            with st.expander("Raw Sources"):
                for src in message["sources"]:
                    st.write(f"- **{src['title']}** ({src['city']})")

        # Feedback logic for assistant messages
        # Use index 'i' in keys to handle duplicate message_ids from repeated queries
        if message["role"] == "assistant" and "message_id" in message and message["message_id"]:
            msg_id = message["message_id"]
            unique_key = f"{i}_{msg_id}"  # Combine index + msg_id for uniqueness

            if msg_id not in st.session_state.feedback_submitted:
                col1, col2, _ = st.columns([0.05, 0.05, 0.9])
                with col1:
                    if st.button("👍", key=f"up_{unique_key}"):
                        if submit_feedback(msg_id, True):
                            st.toast("Thanks for your positive feedback!")
                            st.rerun()
                with col2:
                    if st.button("👎", key=f"down_{unique_key}"):
                        st.session_state[f"show_comment_{unique_key}"] = True

                # Show comment box if thumbs down was clicked
                if st.session_state.get(f"show_comment_{unique_key}"):
                    with st.form(key=f"form_{unique_key}"):
                        comment = st.text_area("How can we improve?", key=f"text_{unique_key}")
                        if st.form_submit_button("Submit"):
                            if submit_feedback(msg_id, False, comment):
                                st.toast("Thanks for your feedback. We will improve!")
                                del st.session_state[f"show_comment_{unique_key}"]
                                st.rerun()
            else:
                st.caption("Feedback received. Thank you!")

# React to user input
if prompt := st.chat_input(f"Ask {CHATBOT_NAME} anything... (e.g., 'jazz concerts this weekend')"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant", avatar="🎭"):
        with st.spinner(f"{CHATBOT_NAME} is searching for events..."):
            try:
                # Prepare request
                headers = {"X-API-Key": API_KEY}
                payload = {"question": prompt, "session_id": st.session_state.session_id}

                # Call FastAPI backend
                response = requests.post(API_URL, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    sources = data.get("sources", [])
                    structured_events = data.get("structured_events", [])
                    msg_id = data.get("message_id")

                    # Display answer
                    st.markdown(answer)

                    # RENDER CARDS IMMEDIATELY FOR NEW MESSAGE
                    if structured_events:
                        st.divider()
                        st.caption(f"Found {len(structured_events)} events:")
                        for event in structured_events:
                            with st.container(border=True):
                                c1, c2 = st.columns([0.7, 0.3])
                                with c1:
                                    st.subheader(event.get("title", "Unknown Event"))
                                    st.text(
                                        f"📍 {event.get('city', 'Unknown City')} • 📅 {event.get('date', 'Unknown Date')}"
                                    )
                                    # Always show times and venue (required fields)
                                    st.text(f"🕐 {event.get('times_display', 'Unknown')}")
                                    st.caption(f"Venue: {event.get('location', 'Unknown')}")
                                with c2:
                                    st.markdown(f"**{event.get('price_label', 'Unknown Price')}**")
                                    st.caption(event.get("age_label", "All Ages"))
                                    if event.get("url"):
                                        st.link_button("More Info", event["url"])

                    # Display Map if available (using sources lat/lon)
                    if sources:
                        # Extract coordinates for mapping
                        map_data = []
                        for src in sources:
                            if src.get("latitude") and src.get("longitude"):
                                map_data.append(
                                    {
                                        "title": src["title"],
                                        "city": src["city"],
                                        "lat": src["latitude"],
                                        "lon": src["longitude"],
                                    }
                                )

                        if map_data:
                            st.divider()
                            st.subheader("Event Locations")
                            # Create a map
                            m = folium.Map(location=[48.8566, 2.3522], zoom_start=10)
                            for loc in map_data:
                                folium.Marker(
                                    [loc["lat"], loc["lon"]],
                                    popup=f"<b>{loc['title']}</b><br>{loc['city']}",
                                    tooltip=loc["title"],
                                ).add_to(m)
                            st_folium(m, returned_objects=[], width=None, height=400)

                    # Add assistant response to chat history
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer,
                            "sources": sources,
                            "structured_events": structured_events,
                            "message_id": msg_id,
                        }
                    )
                    st.rerun()  # Rerun to show feedback buttons for the new message
                elif response.status_code == 400:
                    # Handle safety/guardrail refusals as chat messages
                    try:
                        error_data = response.json()
                        refusal_msg = error_data.get("detail", response.text)
                    except (ValueError, KeyError):
                        refusal_msg = response.text

                    st.session_state.messages.append({"role": "assistant", "content": refusal_msg})
                    st.rerun()
                else:
                    error_msg = f"Error {response.status_code}: {response.text}"
                    st.error(error_msg)

            except Exception as e:
                st.error(f"Failed to connect to backend: {e}")
