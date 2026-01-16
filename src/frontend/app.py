import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import folium_static
import uuid
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Île-de-France Cultural Assistant",
    page_icon="🎭",
    layout="wide"
)

# Constants
API_URL = "http://localhost:8000/api/v1/chat"
API_KEY = "dev-secret-key"  # Matching src/config.py default

# Initialize session state for chat history and session ID
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# Sidebar
with st.sidebar:
    st.title("Settings")
    st.info("This assistant helps you find cultural events in Île-de-France (Paris and surroundings).")
    
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()
    
    st.divider()
    st.caption("v0.1.0 - POC")

# Main UI
st.title("🎭 Île-de-France Cultural Assistant")

# Chat interface
# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "sources" in message and message["sources"]:
            with st.expander("Sources"):
                for src in message["sources"]:
                    st.write(f"- **{src['title']}** ({src['city']})")

# React to user input
if prompt := st.chat_input("What would you like to do in Paris?"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Searching for events..."):
            try:
                # Prepare request
                headers = {"X-API-Key": API_KEY}
                payload = {"question": prompt}
                
                # Call FastAPI backend
                response = requests.post(API_URL, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data["answer"]
                    sources = data["sources"]
                    
                    # Display answer
                    st.markdown(answer)
                    
                    # Display Sources and Map if available
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
                            folium_static(m)
                        
                        with st.expander("Sources"):
                            for src in sources:
                                url_str = f" - [Link]({src['url']})" if src.get('url') else ""
                                st.write(f"- **{src['title']}** ({src['city']}){url_str} (Relevance: {src['score']:.2f})")
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "sources": sources
                    })
                else:
                    error_msg = f"Error {response.status_code}: {response.text}"
                    st.error(error_msg)
                    
            except Exception as e:
                st.error(f"Failed to connect to backend: {e}")