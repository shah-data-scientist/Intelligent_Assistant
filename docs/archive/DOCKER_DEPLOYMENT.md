# Docker Deployment Guide

This guide explains how to deploy the Intelligent Cultural Assistant using Docker and Docker Compose.

## Prerequisites

- **Docker** (version 20.10 or higher)
- **Docker Compose** (version 2.0 or higher)
- **Mistral API Key** (get from [console.mistral.ai](https://console.mistral.ai/))

## Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Intelligent_Assistant
```

### 2. Configure Environment Variables
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Mistral API key
# Required: MISTRAL_API_KEY=your_actual_api_key_here
```

### 3. Prepare Data (First-time Setup)

Ensure you have the required data files:
```bash
# The following files should exist in the data/ directory:
# - events.db (SQLite database with cultural events)
# - faiss_index/ (FAISS vector index directory)
# - chat_history.db (will be created automatically if missing)
```

If you don't have these files, run the data ingestion pipeline first:
```bash
# Install dependencies locally (one-time)
poetry install

# Run data ingestion to populate events.db and faiss_index/
poetry run python -m src.data.ingestion
```

### 4. Build and Run with Docker Compose
```bash
# Build images and start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Services

### FastAPI Backend (`api`)
- **Port:** 8000
- **Health Check:** http://localhost:8000/api/v1/health
- **API Docs:** http://localhost:8000/docs

### Streamlit Frontend (`frontend`)
- **Port:** 8501
- **URL:** http://localhost:8501

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  User Browser                       │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  Streamlit Frontend│  Port: 8501
         │   (Docker Container)│
         └────────┬───────────┘
                  │ HTTP
                  ▼
         ┌────────────────────┐
         │   FastAPI Backend  │  Port: 8000
         │   (Docker Container)│
         └────────┬───────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
   ┌─────────┐        ┌──────────┐
   │SQLite DB│        │FAISS Index│
   │(Volume) │        │ (Volume)  │
   └─────────┘        └──────────┘
```

## Volume Management

The application uses bind mounts to persist data:

- `./data:/app/data` - Contains SQLite databases and FAISS index

**Important:** The `data/` directory is mounted from your host machine, so all data persists across container restarts.

## Environment Variables

### Required
- `MISTRAL_API_KEY` - Your Mistral API key (REQUIRED)

### Optional
- `APP_API_KEY` - API security key (default: "dev-secret-key")
- `LOG_LEVEL` - Logging level (default: "INFO")
- `MAX_EVENTS_TO_FETCH` - Max events to fetch from API (default: 20000)
- `RETRIEVAL_TOP_K` - Number of results to retrieve (default: 10)

See [.env.example](.env.example) for full list of configuration options.

## Development vs Production

### Development (Current Setup)
- Uses `restart: unless-stopped`
- API key defaults to "dev-secret-key"
- CORS allows all origins
- Logs to stdout

### Production Recommendations
1. **Generate a Strong API Key:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Restrict CORS Origins:**
   Edit [src/api/main.py](src/api/main.py) to allow only your frontend domain:
   ```python
   allow_origins=["https://your-domain.com"]
   ```

3. **Use HTTPS:**
   - Deploy behind a reverse proxy (nginx, Traefik)
   - Configure SSL certificates (Let's Encrypt)

4. **Database Backups:**
   ```bash
   # Backup SQLite databases
   docker-compose exec api sqlite3 /app/data/events.db ".backup '/app/data/events_backup.db'"
   ```

5. **Monitor Logs:**
   ```bash
   # Continuous log monitoring
   docker-compose logs -f --tail=100
   ```

## Troubleshooting

### API Container Fails to Start
```bash
# Check logs
docker-compose logs api

# Common issues:
# 1. Missing MISTRAL_API_KEY in .env
# 2. Missing data files (events.db, faiss_index/)
# 3. Port 8000 already in use
```

### Frontend Cannot Connect to API
```bash
# Check API health
curl http://localhost:8000/api/v1/health

# Check frontend logs
docker-compose logs frontend

# Verify API_URL environment variable
docker-compose exec frontend env | grep API_URL
```

### Data Not Persisting
```bash
# Ensure data directory exists and has correct permissions
ls -la ./data/

# Check volume mounts
docker-compose config
```

### No Events in Database
```bash
# Run data ingestion pipeline inside container
docker-compose exec api python -m src.data.ingestion
```

## Useful Commands

### View Container Status
```bash
docker-compose ps
```

### Restart a Service
```bash
docker-compose restart api
docker-compose restart frontend
```

### Rebuild After Code Changes
```bash
docker-compose build
docker-compose up -d
```

### Access Container Shell
```bash
docker-compose exec api bash
docker-compose exec frontend bash
```

### View Resource Usage
```bash
docker stats
```

### Clean Up Everything
```bash
# Stop and remove containers, networks
docker-compose down

# Also remove volumes (WARNING: deletes data!)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

## Performance Tuning

### Resource Limits
Add to `docker-compose.yml` under each service:
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 2G
    reservations:
      cpus: '0.5'
      memory: 1G
```

### Scaling Frontend
```bash
# Run multiple frontend instances for load balancing
docker-compose up -d --scale frontend=3
```

## Security Best Practices

1. Never commit `.env` file to version control
2. Rotate API keys regularly
3. Keep Docker images updated
4. Use non-root users in Dockerfiles (future improvement)
5. Scan images for vulnerabilities: `docker scan cultural-assistant-api`
6. Implement rate limiting in production

## Next Steps

- [ ] Set up CI/CD pipeline for automated builds
- [ ] Deploy to cloud provider (AWS, GCP, Azure)
- [ ] Configure monitoring and alerting (Prometheus, Grafana)
- [ ] Implement automated backups
- [ ] Add integration tests for Docker deployment

## Support

For issues or questions:
1. Check logs: `docker-compose logs`
2. Review [troubleshooting section](#troubleshooting)
3. Open an issue on GitHub
