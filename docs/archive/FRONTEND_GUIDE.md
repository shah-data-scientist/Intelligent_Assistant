# Frontend User Guide

## Overview

The Intelligent Cultural Assistant features a modern Streamlit web interface that provides an intuitive chat experience for discovering cultural events in Île-de-France.

## Features

### 🎭 Modern Chat Interface
- Real-time conversational AI powered by Mistral
- Multi-language support (French/English)
- Chat history maintained during session
- Streaming responses for better UX

### 🗺️ Interactive Map
- Visualize event locations on an interactive map
- Folium-powered mapping with OpenStreetMap
- Click markers to see event details
- Automatic city geocoding

### 📊 Data Visualization
- Score distribution charts (similarity scores)
- Events by city bar charts
- Detailed source event tables
- Real-time statistics

### ⚙️ Configuration
- Language selector (FR/EN)
- API status monitoring
- Session management
- Clear conversation button

## Getting Started

### Prerequisites

1. **API Server Running**
   ```bash
   poetry run uvicorn src.api.main:app --host 127.0.0.1 --port 8000
   ```

2. **Environment Variables**
   - Ensure `.env` file contains `MISTRAL_API_KEY`
   - Default API key: `dev-secret-key` (matches `APP_API_KEY` in settings)

### Starting the Frontend

#### Option 1: Using Helper Script
```bash
poetry run python scripts/run_frontend.py
```

#### Option 2: Direct Streamlit Command
```bash
poetry run streamlit run src/frontend/app.py
```

#### Option 3: Custom Configuration
```bash
poetry run streamlit run src/frontend/app.py \
  --server.address=localhost \
  --server.port=8501 \
  --server.headless=true
```

### Accessing the Application

Once started, open your browser and navigate to:
```
http://localhost:8501
```

## User Interface

### Main Layout

```
┌─────────────────────────────────────────────────────┐
│  🎭 Assistant Culturel Intelligent                  │
│  Découvrez les événements culturels en Île-de-France│
├───────────────┬─────────────────────────────────────┤
│   Sidebar     │         Chat Area                   │
│               │                                     │
│ ⚙️ Config     │  💬 Conversation                    │
│ 🌍 Language   │  [User messages]                    │
│ 💡 Usage Tips │  [AI responses]                     │
│ 📊 Stats      │                                     │
│ 🗑️ Clear      │  [Chat input box]                   │
│ 🔌 API Status │                                     │
│               ├─────────────────────────────────────┤
│               │  📚 Sources | 🗺️ Map | 📊 Stats   │
│               │  [Event details and visualizations] │
└───────────────┴─────────────────────────────────────┘
```

### Sidebar Components

#### 1. Configuration
- **Language Selector**: Choose between French 🇫🇷 and English 🇬🇧
- Affects both query interpretation and response language

#### 2. Usage Tips
Example questions to get started:
- "Quels concerts de jazz ce mois-ci ?"
- "Expositions d'art à Paris"
- "Événements gratuits ce weekend"

#### 3. Statistics (After Query)
- Number of events found
- Cities with events
- Real-time metrics

#### 4. Session Controls
- **Nouvelle conversation**: Clear chat history and start fresh

#### 5. API Status
- ✅ Connected: API is responding
- ❌ Error: Connection issues or API down

### Chat Interface

#### Asking Questions

1. **Type your question** in the chat input at the bottom
2. **Press Enter** or click Send
3. **Wait for response** (2-7 seconds typical)
4. **View answer** with AI-generated recommendations
5. **Explore sources** in tabs below

#### Example Queries

**French:**
```
Quels sont les meilleurs événements culturels ce weekend à Paris ?
Y a-t-il des concerts de musique classique en mars ?
Trouve-moi des expositions d'art contemporain
```

**English:**
```
What cultural events are happening this weekend?
Show me jazz concerts in Paris
Find theater performances for children
```

### Source Events Display

After each query, view the retrieved source events in three ways:

#### 📚 Sources Tab
- **Table View**: Quick overview of all events
  - Title
  - City
  - Date
  - Similarity Score

- **Detailed Cards**: Expandable view with:
  - Full event titles
  - Location details
  - Dates and times
  - Direct links to event pages
  - Similarity scores

#### 🗺️ Map Tab
- **Interactive Map**: Visualize event locations
  - Blue markers for each event
  - Click markers for event details
  - Zoom and pan controls
  - OpenStreetMap tiles

#### 📊 Statistics Tab
- **Score Distribution**: Histogram of similarity scores
- **Events by City**: Bar chart showing event distribution
- **Insights**: Visual analysis of search results

## Features in Detail

### Multi-Language Support

The application automatically detects your query language and responds accordingly:

- **French Queries** → French Responses
- **English Queries** → English Responses

You can also explicitly set the language using the sidebar selector.

### Session Management

- **Persistent Chat**: Messages stay during your session
- **Source History**: Last query's sources displayed
- **Statistics**: Updated after each query
- **Clear Anytime**: Reset conversation with one click

### Error Handling

The application provides clear error messages:

| Error | Meaning | Solution |
|-------|---------|----------|
| ❌ Erreur d'authentification | API key mismatch | Check `APP_API_KEY` in `.env` |
| ❌ Le système RAG n'est pas initialisé | API not ready | Wait for API startup (~7s) |
| ❌ La requête a expiré | Timeout | Retry query |
| ❌ Impossible de se connecter | API not running | Start API server |

### Performance

- **Initial Load**: 2-3 seconds (Streamlit startup)
- **Query Response**: 2-7 seconds (AI processing)
- **Map Rendering**: <1 second
- **Chart Generation**: <1 second

## Configuration

### API Connection

The frontend connects to the FastAPI backend using these settings:

```python
API_BASE_URL = "http://localhost:8000/api/v1"
API_KEY = "dev-secret-key"
```

To change these, modify [src/frontend/app.py](../src/frontend/app.py):
- Line 39: `API_BASE_URL`
- Line 40: `API_KEY`

**Production**: Store API key in environment variable or secrets management.

### Streamlit Configuration

Create `.streamlit/config.toml` for custom settings:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#f8f9fa"
secondaryBackgroundColor = "#ffffff"
textColor = "#262730"
font = "sans serif"

[server]
port = 8501
address = "localhost"
headless = true

[browser]
gatherUsageStats = false
```

## Troubleshooting

### Frontend Won't Start

**Issue**: Streamlit fails to start

**Solutions:**
1. Check if port 8501 is available:
   ```bash
   netstat -ano | findstr :8501
   ```
2. Kill existing Streamlit process
3. Try different port:
   ```bash
   streamlit run src/frontend/app.py --server.port=8502
   ```

### Can't Connect to API

**Issue**: "❌ API non disponible" in sidebar

**Solutions:**
1. Start API server:
   ```bash
   poetry run uvicorn src.api.main:app --host 127.0.0.1 --port 8000
   ```
2. Check API health:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
3. Verify API key matches in both frontend and backend

### Map Not Displaying

**Issue**: Map tab is blank or shows errors

**Solutions:**
1. Check if events have city information
2. Verify folium and streamlit-folium are installed:
   ```bash
   poetry show streamlit-folium
   ```
3. Clear browser cache

### Charts Not Rendering

**Issue**: Statistics tab shows no charts

**Solutions:**
1. Ensure plotly is installed:
   ```bash
   poetry show plotly
   ```
2. Check if source events contain required fields
3. Try clearing Streamlit cache:
   - Press `C` in the app
   - Select "Clear cache"

### Slow Performance

**Issue**: App feels sluggish

**Solutions:**
1. Check API response time (should be 2-7s)
2. Reduce number of events displayed
3. Clear browser cache
4. Restart Streamlit app

## Advanced Usage

### Custom Styling

Modify CSS in [src/frontend/app.py](../src/frontend/app.py) (lines 18-43) to customize:
- Colors
- Fonts
- Card styles
- Layout spacing

### Adding New Features

The app is modular and easy to extend:

**Add New Tab:**
```python
with st.tabs(["Tab1", "Tab2", "New Tab"]):
    with tab3:
        st.markdown("### New Feature")
        # Your code here
```

**Add Sidebar Widget:**
```python
with st.sidebar:
    new_setting = st.slider("Setting", 0, 100, 50)
```

**Add New Visualization:**
```python
import plotly.express as px

fig = px.scatter(df, x="date", y="score")
st.plotly_chart(fig, use_container_width=True)
```

## Security Notes

### API Key

**Development:**
- Default key: `dev-secret-key`
- Hardcoded in `app.py` for convenience

**Production:**
- Use environment variables:
  ```python
  import os
  API_KEY = os.getenv("FRONTEND_API_KEY")
  ```
- Implement OAuth or session-based auth
- Use Streamlit secrets management

### CORS

The API allows all origins by default. In production:
1. Restrict CORS in [src/api/main.py](../src/api/main.py)
2. Whitelist only your frontend domain

## Best Practices

### User Experience

1. **Clear Instructions**: Provide example queries
2. **Error Messages**: Make them actionable
3. **Loading States**: Show spinners during processing
4. **Visual Feedback**: Use colors and icons

### Performance

1. **Caching**: Use `@st.cache_data` for expensive operations
2. **Lazy Loading**: Load data only when needed
3. **Pagination**: For large result sets
4. **Debouncing**: Avoid excessive API calls

### Accessibility

1. **Alt Text**: Provide descriptions for images
2. **Keyboard Navigation**: Ensure all features accessible
3. **Color Contrast**: Maintain readability
4. **Screen Readers**: Use semantic HTML

## Deployment

### Local Network

Share with colleagues on your network:

```bash
streamlit run src/frontend/app.py --server.address=0.0.0.0
```

Access at: `http://<your-ip>:8501`

### Docker (Future)

See [Docker Deployment Guide](./DOCKER_GUIDE.md) for containerization.

### Cloud Hosting

**Streamlit Cloud:**
1. Push to GitHub
2. Connect to Streamlit Cloud
3. Configure secrets
4. Deploy

**Other Options:**
- Heroku
- Google Cloud Run
- AWS Elastic Beanstalk
- Azure App Service

## Support

### Getting Help

**Issues:**
- Check [Troubleshooting](#troubleshooting) section
- Review logs in terminal
- Inspect browser console (F12)

**Documentation:**
- [Streamlit Docs](https://docs.streamlit.io)
- [API Usage Guide](./API_USAGE_GUIDE.md)
- [Project README](../README.md)

### Logs

**Streamlit Logs:**
- Displayed in terminal where app was started
- Use `--log_level=debug` for verbose output

**API Logs:**
- Check API terminal output
- Review `api_server.log` if configured

## Future Enhancements

Planned features for future releases:

- [ ] **Authentication**: User login and session management
- [ ] **Favorites**: Save preferred events
- [ ] **Filters**: Advanced date/category/location filters
- [ ] **Notifications**: Alert for new matching events
- [ ] **Export**: Download results as PDF/CSV
- [ ] **Calendar Integration**: Add events to calendar
- [ ] **Social Sharing**: Share recommendations
- [ ] **Feedback**: Rate recommendations quality

## Technical Stack

**Frontend:**
- Streamlit 1.53+
- Plotly 6.5+ (charts)
- Folium 0.20+ (maps)
- Streamlit-Folium 0.26+ (integration)

**Backend:**
- FastAPI (REST API)
- LangChain (RAG orchestration)
- Mistral AI (embeddings + LLM)
- FAISS (vector search)

**Data:**
- 1,000+ events from OpenAgenda
- Île-de-France region
- 2026-2027 timeframe

## Contact

For questions or contributions:
- GitHub: [Repository URL]
- Email: shah.data.scientist@gmail.com
