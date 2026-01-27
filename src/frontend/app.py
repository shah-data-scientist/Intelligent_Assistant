import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
import uuid
import os
from datetime import datetime

# Import centralized config for chatbot identity
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.config import settings

# Page configuration - Uses centralized chatbot name from config
st.set_page_config(
    page_title=f"{settings.chatbot_name} - Your Cultural Guide",
    page_icon="🎭",
    layout="wide"
)

# Constants - Read from environment variables (for Docker) or use defaults (for local dev)
API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1/chat")
API_KEY = os.getenv("API_KEY", "dev-secret-key")

# Chatbot name and personality - From centralized config
CHATBOT_NAME = settings.chatbot_name
CHATBOT_EMOJI = "🎭"

# Bilingual welcome messages - Uses centralized chatbot name
WELCOME_EN = f"""
### Hey there! I'm **{settings.chatbot_name}** 🎭

*I'm your friendly guide here to illuminate the cultural treasures of Paris and Ile-de-France!*

**What can I help you discover?**
- 🎵 **Music** — Jazz nights, classical concerts, rock shows
- 🎨 **Art** — Exhibitions, galleries, installations
- 🎭 **Theater** — Drama, comedy, musicals
- 🎪 **Festivals** — Street fairs, cultural celebrations

**Just ask me things like:**
- *"Jazz concerts this weekend in Paris"*
- *"Free exhibitions near Versailles"*
- *"Family-friendly events in February"*

**Good to know:**
- 📅 I know about **1,000+ events** from Jan 2026 to Jan 2027
- 🗣️ I speak English & French — tu peux me parler en francais !
- 🔍 If I can't find exactly what you want, I'll suggest nearby alternatives

*Ready to explore? Ask me anything!* ✨
"""

WELCOME_FR = f"""
### Salut ! Moi c'est **{settings.chatbot_name}** 🎭

*Je suis votre guide amicale, la pour illuminer les tresors culturels de Paris et l'Ile-de-France !*

**Qu'est-ce que je peux vous aider a decouvrir ?**
- 🎵 **Musique** — Soirees jazz, concerts classiques, rock
- 🎨 **Art** — Expositions, galeries, installations
- 🎭 **Theatre** — Drame, comedie, comedies musicales
- 🎪 **Festivals** — Fetes de rue, celebrations culturelles

**Posez-moi des questions comme :**
- *"Concerts de jazz ce week-end a Paris"*
- *"Expositions gratuites pres de Versailles"*
- *"Evenements famille en fevrier"*

**Bon a savoir :**
- 📅 Je connais **1 000+ evenements** de jan. 2026 a jan. 2027
- 🗣️ Je parle francais et anglais — you can talk to me in English!
- 🔍 Si je ne trouve pas exactement ce que vous cherchez, je proposerai des alternatives proches

*Pret(e) a explorer ? Demandez-moi n'importe quoi !* ✨
"""

# Initialize session state for chat history and session ID
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "__WELCOME__", "is_welcome": True}]

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "feedback_submitted" not in st.session_state:
    st.session_state.feedback_submitted = set()

# Sidebar
with st.sidebar:
    st.title(f"🎭 {CHATBOT_NAME}")
    st.caption("*Your cultural events companion*")
    st.divider()

    st.subheader("⚙️ Settings")
    st.info(f"Session: `{st.session_state.session_id[:8]}...`")

    if st.button("🔄 Start Fresh"):
        st.session_state.messages = [{"role": "assistant", "content": "__WELCOME__", "is_welcome": True}]
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.feedback_submitted = set()
        st.rerun()

    st.divider()
    st.subheader("💡 Quick Tips")
    st.markdown("""
    - Be specific: *"jazz in Paris this weekend"*
    - Ask in French or English
    - Ask follow-ups: *"tell me more about the first one"*
    """)

    st.divider()
    st.caption(f"v1.0.0 — {settings.chatbot_name} by OpenClassrooms")

# Main UI
st.title(f"{CHATBOT_EMOJI} Meet {CHATBOT_NAME} — Your Cultural Guide")

# Function to submit feedback to API
def submit_feedback(message_id, is_positive, comment=""):
    try:
        headers = {"X-API-Key": API_KEY}
        payload = {
            "message_id": message_id,
            "is_positive": is_positive,
            "comment": comment
        }
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
    # Special handling for welcome message - two column layout
    if message.get("is_welcome"):
        with st.chat_message("assistant", avatar="🎭"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(WELCOME_EN)
            with col2:
                st.markdown(WELCOME_FR)
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
                        if event.get("times_display"):
                            st.text(f"🕐 {event.get('times_display')}")
                        if event.get("location"):
                            st.caption(f"Venue: {event.get('location')}")
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
        if message["role"] == "assistant" and "message_id" in message and message["message_id"]:
            msg_id = message["message_id"]
            
            if msg_id not in st.session_state.feedback_submitted:
                col1, col2, _ = st.columns([0.05, 0.05, 0.9])
                with col1:
                    if st.button("👍", key=f"up_{msg_id}"):
                        if submit_feedback(msg_id, True):
                            st.toast("Thanks for your positive feedback!")
                            st.rerun()
                with col2:
                    if st.button("👎", key=f"down_{msg_id}"):
                        st.session_state[f"show_comment_{msg_id}"] = True
                
                # Show comment box if thumbs down was clicked
                if st.session_state.get(f"show_comment_{msg_id}"):
                    with st.form(key=f"form_{msg_id}"):
                        comment = st.text_area("How can we improve?", key=f"text_{msg_id}")
                        if st.form_submit_button("Submit"):
                            if submit_feedback(msg_id, False, comment):
                                st.toast("Thanks for your feedback. We will improve!")
                                del st.session_state[f"show_comment_{msg_id}"]
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
                payload = {
                    "question": prompt,
                    "session_id": st.session_state.session_id
                }
                
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
                                    st.text(f"📍 {event.get('city', 'Unknown City')} • 📅 {event.get('date', 'Unknown Date')}")
                                    if event.get("location"):
                                        st.caption(f"Venue: {event.get('location')}")
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
                                map_data.append({
                                    "title": src["title"],
                                    "city": src["city"],
                                    "lat": src["latitude"],
                                    "lon": src["longitude"]
                                })
                        
                        if map_data:
                            st.divider()
                            st.subheader("Event Locations")
                            # Create a map
                            m = folium.Map(location=[48.8566, 2.3522], zoom_start=10)
                            for loc in map_data:
                                folium.Marker(
                                    [loc["lat"], loc["lon"]],
                                    popup=f"<b>{loc['title']}</b><br>{loc['city']}",
                                    tooltip=loc["title"]
                                ).add_to(m)
                            st_folium(m, returned_objects=[], width=None, height=400)
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "sources": sources,
                        "structured_events": structured_events,
                        "message_id": msg_id
                    })
                    st.rerun() # Rerun to show feedback buttons for the new message
                elif response.status_code == 400:
                    # Handle safety/guardrail refusals as chat messages
                    try:
                        error_data = response.json()
                        refusal_msg = error_data.get("detail", response.text)
                    except:
                        refusal_msg = response.text
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": refusal_msg
                    })
                    st.rerun()
                else:
                    error_msg = f"Error {response.status_code}: {response.text}"
                    st.error(error_msg)
                    
            except Exception as e:
                st.error(f"Failed to connect to backend: {e}")