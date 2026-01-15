"""Streamlit frontend for the Intelligent Cultural Assistant.

A modern chat interface for discovering cultural events in Île-de-France.
"""

import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from datetime import datetime, timedelta
from typing import Dict, List, Any
import plotly.express as px
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Cultural Events Assistant",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stChatMessage {
        background-color: white;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .event-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .event-title {
        font-weight: bold;
        color: #1f77b4;
        font-size: 1.1rem;
    }
    .event-meta {
        color: #666;
        font-size: 0.9rem;
    }
    h1 {
        color: #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
API_KEY = "dev-secret-key"  # Should match settings.app_api_key

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sources" not in st.session_state:
    st.session_state.sources = []
if "language" not in st.session_state:
    st.session_state.language = "fr"

def call_api(question: str, language: str = None) -> Dict[str, Any]:
    """Call the FastAPI backend to get a response.

    Args:
        question: User's question
        language: Preferred language (fr/en)

    Returns:
        API response containing answer and sources

    Raises:
        requests.RequestException: If API call fails
    """
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    payload = {"question": question}
    if language:
        payload["language"] = language

    response = requests.post(
        f"{API_BASE_URL}/chat",
        json=payload,
        headers=headers,
        timeout=30
    )
    response.raise_for_status()
    return response.json()

def create_events_map(sources: List[Dict[str, Any]]) -> folium.Map:
    """Create a folium map with event markers.

    Args:
        sources: List of source events from API

    Returns:
        Folium map object
    """
    # Default center: Paris
    center_lat, center_lon = 48.8566, 2.3522

    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles="OpenStreetMap"
    )

    # Add markers for events with locations
    for idx, source in enumerate(sources):
        if source.get("city"):
            # Approximate coordinates for common Île-de-France cities
            city_coords = {
                "Paris": (48.8566, 2.3522),
                "Versailles": (48.8049, 2.1204),
                "Saint-Denis": (48.9362, 2.3574),
                "Boulogne-Billancourt": (48.8353, 2.2394),
                "Montreuil": (48.8617, 2.4431),
                "Nanterre": (48.8925, 2.1972),
                "Créteil": (48.7897, 2.4555),
            }

            city = source["city"]
            coords = city_coords.get(city, (center_lat, center_lon))

            # Create popup content
            popup_html = f"""
                <div style="font-family: Arial; min-width: 200px;">
                    <h4 style="color: #1f77b4; margin-bottom: 5px;">{source.get('title', 'Unknown')}</h4>
                    <p style="margin: 3px 0;"><b>📍 Ville:</b> {city}</p>
                    <p style="margin: 3px 0;"><b>📅 Date:</b> {source.get('date', 'N/A')}</p>
                    <p style="margin: 3px 0;"><b>⭐ Score:</b> {source.get('score', 0):.2f}</p>
                    {f'<p style="margin: 3px 0;"><a href="{source["url"]}" target="_blank">🔗 Plus d\'infos</a></p>' if source.get('url') else ''}
                </div>
            """

            folium.Marker(
                location=coords,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=source.get('title', 'Event'),
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(m)

    return m

def display_sources(sources: List[Dict[str, Any]]):
    """Display source events in an organized way.

    Args:
        sources: List of source events from API
    """
    if not sources:
        return

    st.markdown("### 📚 Événements Sources")

    # Create DataFrame for table display
    df_data = []
    for source in sources:
        df_data.append({
            "Titre": source.get("title", "N/A"),
            "Ville": source.get("city", "N/A"),
            "Date": source.get("date", "N/A"),
            "Score": f"{source.get('score', 0):.2f}",
        })

    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Display detailed cards
        with st.expander("Voir les détails"):
            for idx, source in enumerate(sources, 1):
                st.markdown(f"""
                <div class="event-card">
                    <div class="event-title">{idx}. {source.get('title', 'Unknown Event')}</div>
                    <div class="event-meta">
                        📍 {source.get('city', 'N/A')} |
                        📅 {source.get('date', 'N/A')} |
                        ⭐ Similarité: {source.get('score', 0):.2f}
                    </div>
                    {f'<a href="{source["url"]}" target="_blank">🔗 En savoir plus</a>' if source.get('url') else ''}
                </div>
                """, unsafe_allow_html=True)

# Main title
st.title("🎭 Assistant Culturel Intelligent")
st.markdown("Découvrez les événements culturels en Île-de-France grâce à l'IA")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")

    # Language selection
    language = st.selectbox(
        "🌍 Langue / Language",
        options=["fr", "en"],
        format_func=lambda x: "🇫🇷 Français" if x == "fr" else "🇬🇧 English",
        index=0 if st.session_state.language == "fr" else 1
    )
    st.session_state.language = language

    st.markdown("---")

    # Information
    st.markdown("### 💡 Comment utiliser")
    st.markdown("""
    1. Posez une question sur les événements culturels
    2. L'IA cherche dans 1000+ événements
    3. Recevez des recommandations personnalisées

    **Exemples de questions:**
    - Quels concerts de jazz ce mois-ci ?
    - Expositions d'art à Paris
    - Événements gratuits ce weekend
    """)

    st.markdown("---")

    # Statistics
    if st.session_state.sources:
        st.markdown("### 📊 Statistiques")
        st.metric("Événements trouvés", len(st.session_state.sources))

        cities = [s.get("city", "N/A") for s in st.session_state.sources if s.get("city")]
        if cities:
            st.markdown(f"**Villes:** {', '.join(set(cities))}")

    st.markdown("---")

    # Clear conversation
    if st.button("🗑️ Nouvelle conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.sources = []
        st.rerun()

    # API Status
    st.markdown("---")
    st.markdown("### 🔌 Statut API")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            st.success("✅ Connecté")
        else:
            st.error("❌ Erreur de connexion")
    except:
        st.error("❌ API non disponible")

# Main chat area
st.markdown("### 💬 Conversation")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Posez votre question sur les événements culturels..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    with st.chat_message("assistant"):
        with st.spinner("Recherche en cours..."):
            try:
                response = call_api(prompt, st.session_state.language)
                answer = response["answer"]
                sources = response["sources"]

                # Display answer
                st.markdown(answer)

                # Store in session
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.session_state.sources = sources

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    st.error("❌ Erreur d'authentification. Vérifiez la clé API.")
                elif e.response.status_code == 503:
                    st.error("❌ Le système RAG n'est pas initialisé. Démarrez l'API.")
                else:
                    st.error(f"❌ Erreur HTTP: {e.response.status_code}")
            except requests.exceptions.Timeout:
                st.error("❌ La requête a expiré. Réessayez.")
            except requests.exceptions.ConnectionError:
                st.error("❌ Impossible de se connecter à l'API. Assurez-vous qu'elle est démarrée.")
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")

# Display sources and map below chat
if st.session_state.sources:
    st.markdown("---")

    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📚 Sources", "🗺️ Carte", "📊 Statistiques"])

    with tab1:
        display_sources(st.session_state.sources)

    with tab2:
        st.markdown("### 🗺️ Localisation des événements")
        events_map = create_events_map(st.session_state.sources)
        st_folium(events_map, width=None, height=400)

    with tab3:
        st.markdown("### 📊 Analyse des événements")

        # Score distribution
        scores = [s.get("score", 0) for s in st.session_state.sources]
        if scores:
            fig_scores = px.histogram(
                x=scores,
                labels={"x": "Score de similarité", "y": "Nombre d'événements"},
                title="Distribution des scores de similarité",
                nbins=10
            )
            st.plotly_chart(fig_scores, use_container_width=True)

        # Cities distribution
        cities = [s.get("city", "Unknown") for s in st.session_state.sources]
        if cities:
            city_counts = pd.Series(cities).value_counts()
            fig_cities = px.bar(
                x=city_counts.index,
                y=city_counts.values,
                labels={"x": "Ville", "y": "Nombre d'événements"},
                title="Événements par ville"
            )
            st.plotly_chart(fig_cities, use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🤖 Propulsé par Mistral AI & LangChain |
        📊 1000+ événements indexés |
        🔍 Recherche sémantique avec FAISS</p>
    </div>
    """,
    unsafe_allow_html=True
)
