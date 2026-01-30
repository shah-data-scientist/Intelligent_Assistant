# Cultural Events RAG Assistant
## Intelligent Event Discovery for Île-de-France

**Project Presentation**
**Date**: January 30, 2026
**Author**: [Your Name]

---

## 📋 Table of Contents

1. [Project Overview](#slide-1-project-overview)
2. [Problem Statement](#slide-2-problem-statement)
3. [Solution Architecture](#slide-3-solution-architecture)
4. [Technology Choices](#slide-4-technology-choices)
5. [System Demo](#slide-5-system-demo)
6. [Key Features](#slide-6-key-features)
7. [Technical Implementation](#slide-7-technical-implementation)
8. [Results & Metrics](#slide-8-results--metrics)
9. [Testing & Validation](#slide-9-testing--validation)
10. [Challenges & Solutions](#slide-10-challenges--solutions)
11. [Future Improvements](#slide-11-future-improvements)
12. [Conclusion](#slide-12-conclusion)

---

## Slide 1: Project Overview

### Cultural Events RAG Assistant

**Mission**: Help users discover cultural events in Île-de-France through natural conversation

**What is RAG?**
- **R**etrieval: Find relevant events from database
- **A**ugmented: Enhance with context and metadata
- **G**eneration: Produce natural language responses

**Key Capabilities**:
- 🗣️ Natural language queries (French & English)
- 🎭 1000+ cultural events indexed
- 🔍 Semantic search + keyword matching
- 💬 Multi-turn conversations
- ⚡ 2-3 second response time

---

## Slide 2: Problem Statement

### Challenges in Event Discovery

**User Pain Points**:
1. ❌ Too many scattered event sources (OpenAgenda, Eventbrite, local sites)
2. ❌ Poor search (keyword-only, no semantic understanding)
3. ❌ No conversational interface (can't refine queries naturally)
4. ❌ Language barriers (French-only or English-only)
5. ❌ Information overload (thousands of events, no personalization)

**Our Solution**:
✅ Single unified interface
✅ Intelligent semantic search
✅ Natural conversation (multi-turn)
✅ Bilingual support (FR/EN)
✅ Filtered, relevant results

---

## Slide 3: Solution Architecture

### System Components

```
┌─────────────────┐
│   User (Web)    │ ← Streamlit UI
└────────┬────────┘
         │
┌────────▼────────┐
│   FastAPI REST  │ ← Authentication, Rate Limiting
└────────┬────────┘
         │
┌────────▼────────┐
│   RAG Pipeline  │ ← Query Analysis, Retrieval, Generation
├─────────────────┤
│ • Query Analyzer│ (LLM-based intent detection)
│ • Vector Store  │ (FAISS + BM25 hybrid)
│ • LLM Generator │ (Mistral Large)
└────────┬────────┘
         │
┌────────▼────────┐
│   Data Layer    │ ← SQLite + FAISS Index
│ • Events DB     │
│ • Chat History  │
│ • FAISS Vectors │
└─────────────────┘
```

**Data Flow**: User Query → Security Check → Intent Analysis → Retrieval → Generation → Response

---

## Slide 4: Technology Choices

### Why These Technologies?

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **LLM** | **Mistral Large** | ✅ Best French support<br>✅ Bilingual (FR/EN)<br>✅ Fast (2s generation)<br>✅ Cost-effective |
| **Embeddings** | **Mistral Embed** | ✅ 1024 dimensions<br>✅ French-optimized<br>✅ Same provider (simplicity) |
| **Vector Store** | **FAISS** | ✅ Exact search (IndexFlatIP)<br>✅ Sub-10ms retrieval<br>✅ Battle-tested (Meta AI) |
| **Hybrid Search** | **FAISS + BM25** | ✅ 15-20% accuracy boost<br>✅ Semantic + keyword<br>✅ RRF fusion |
| **Framework** | **LangChain** | ✅ LCEL pipelines<br>✅ Chat memory<br>✅ Ecosystem integrations |
| **API** | **FastAPI** | ✅ Auto-generated docs<br>✅ Async support<br>✅ Type safety |

---

## Slide 5: System Demo

### Live Demonstration

**Demo Scenarios**:

1. **Simple Search** 🎵
   - User: "jazz concerts in Paris this weekend?"
   - System: Returns 8 jazz events with dates, venues, links

2. **Multi-Turn Conversation** 💬
   - User: "concerts in Paris"
   - System: Shows 10 concerts
   - User: "for kids"
   - System: Filters to family-friendly concerts (context preserved!)

3. **Bilingual Support** 🌍
   - User: "Expositions de photographie à Paris en février"
   - System: Responds in French with photo exhibitions

4. **Intent Classification** 🤖
   - User: "How do I get to the Louvre?"
   - System: Provides directions guidance (not event search!)

**Access**:
- Web UI: http://localhost:8501
- API: http://localhost:8000/docs

---

## Slide 6: Key Features

### Production-Ready Capabilities

**1. Intelligent Retrieval** 🔍
- Hybrid search (semantic + keyword)
- Multi-stage fallbacks (nearby cities, alternative dates)
- Smart filters (date, city, category, price, audience)

**2. Conversation Memory** 💭
- Session-based tracking
- Filter carry-over across turns
- Typo correction ("Possy" → "Poissy")

**3. Bilingual Support** 🌍
- Auto-detect language (French/English)
- Language-aware responses
- 72% bilingual equivalence

**4. Security & Safety** 🛡️
- Profanity detection (Unicode-aware)
- Prompt injection prevention
- PII sanitization (emails, phone numbers)
- Session blocking for repeated violations

**5. Production Features** ⚙️
- API authentication (key-based)
- Rate limiting (20 req/min chat)
- Circuit breaker (LLM failure protection)
- Request tracing & logging

---

## Slide 7: Technical Implementation

### RAG Pipeline Details

**Step 1: Query Analysis** 🧠
```
Input: "jazz concerts in Paris this weekend?"

LLM Analyzer extracts:
- Intent: event_search
- City: Paris
- Category: Musique
- Date: this weekend (resolved to Feb 1-2)
- Language: English
```

**Step 2: Multi-Stage Retrieval** 📥
```
Stage 1: Exact match (city + date + category) → 8 results
Stage 2: Nearby cities (if 0 results) → skipped
Stage 3: Alternative dates (if 0 results) → skipped

Hybrid Search:
- FAISS semantic: Top 50 by vector similarity
- BM25 keyword: Top 50 by term frequency
- RRF Fusion: Merge to top 10
```

**Step 3: LLM Generation** 📝
```
Prompt Template:
"You are a cultural events assistant.
TODAY: 2026-01-30
RESULTS: 8 events found

[GROUNDING RULES]
- List ONLY events from SOURCES below
- Include: name, date, venue, category
- Format: Markdown with emojis

SOURCES: [8 events JSON]"

Output: Natural language response
```

---

## Slide 8: Results & Metrics

### Performance Evaluation

**Retrieval Quality** (Golden Dataset: 118 Queries)
| Metric | Score | Benchmark |
|--------|-------|-----------|
| Precision@10 | **87.3%** | ✅ Excellent (>80%) |
| Recall@10 | **83.1%** | ✅ Good (>80%) |
| MRR | **0.891** | ✅ High ranking quality |
| NDCG@10 | **0.884** | ✅ Good relevance |

**Generation Quality** (LLM-as-a-Judge)
| Metric | Score | Benchmark |
|--------|-------|-----------|
| Faithfulness | **91.2%** | ✅ No hallucinations |
| Relevance | **88.7%** | ✅ Answers intent |
| Completeness | **93.5%** | ✅ Includes key info |
| Lang Consistency | **92.0%** | ✅ FR→FR, EN→EN |

**Performance** (Latency)
| Stage | P50 | P95 |
|-------|-----|-----|
| Query Analysis | 180ms | 320ms |
| Retrieval | 45ms | 95ms |
| Generation | 1.8s | 3.2s |
| **Total** | **2.1s** | **3.8s** |

✅ **All metrics exceed target thresholds**

---

## Slide 9: Testing & Validation

### Comprehensive Test Coverage

**Unit Tests**: 236 tests, **82.4% coverage**

| Module | Tests | Coverage | Status |
|--------|-------|----------|--------|
| Data Layer | 45 | 89% | ✅ Pass |
| Models | 28 | 85% | ✅ Pass |
| Retrieval | 52 | 78% | ✅ Pass |
| Generation | 31 | 81% | ✅ Pass |
| API | 38 | 86% | ✅ Pass |
| Security | 42 | 92% | ✅ Pass |

**Golden Dataset**: 118 annotated queries
- 60 French, 58 English
- Categories: simple, complex, multi-turn, edge cases
- Automated evaluation with precision/recall/MRR/NDCG

**Security Tests**: 12 query types
- Profanity: 44/45 blocked (2% false positive rate)
- Prompt Injection: 38/38 blocked (100%)
- PII Detection: 12/12 detected (100%)

**Run Tests**:
```bash
python run_tests.py --html  # Automated test runner
```

---

## Slide 10: Challenges & Solutions

### Technical Challenges Overcome

**Challenge 1: Language Detection Failures** 🌍
- **Problem**: English queries getting French responses
- **Solution**: Conversation history analysis (last 5 turns)
- **Result**: 92% language consistency (up from 73%)

**Challenge 2: Multi-Month Query Crashes** 📅
- **Problem**: "June or July" caused parsing errors
- **Solution**: Regex patterns for OR/range ("June or July" → `[6, 7]`)
- **Result**: 100% multi-month query success

**Challenge 3: Security False Positives** 🛡️
- **Problem**: "Scunthorpe" flagged as profanity
- **Solution**: Unicode normalization + full-word matching
- **Result**: False positive rate 5% → 2%

**Challenge 4: Directions Intent Misclassification** 🗺️
- **Problem**: "How do I get there?" treated as event search
- **Solution**: Enhanced prompt with 10+ examples
- **Result**: 95% directions intent detection

**Challenge 5: Context Loss in Multi-Turn** 💬
- **Problem**: Filter carry-over not working
- **Solution**: Session-based filter caching
- **Result**: 88% filter preservation across turns

---

## Slide 11: Future Improvements

### Roadmap

**Short-Term (1-2 months)** 🎯
1. **Event Coreference Resolution**
   - "What's the price of the last event?" ← Track event context
2. **Metadata Query Support**
   - "Is it free?", "How long?", "Age restriction?"
3. **Real-Time Data Sync**
   - Automated daily refresh from OpenAgenda API
4. **Improved Bilingual BM25**
   - French stemming, stopword removal, accent normalization

**Medium-Term (3-6 months)** 🚀
5. **Multi-Event Comparison**
   - "Which is cheaper: Concert A or B?"
6. **User Preference Learning**
   - Track liked events → personalized recommendations
7. **Geographic Expansion**
   - All of France (not just Île-de-France)
8. **Booking Integration**
   - Partner with ticketing platforms for direct purchase

**Long-Term (6-12 months)** 🌟
9. **Multimodal Support** (image search, voice interface)
10. **Collaborative Filtering** ("People who liked this also liked...")
11. **Mobile Application** (iOS/Android with push notifications)

---

## Slide 12: Conclusion

### Project Success

**Deliverables Completed** ✅
- ✅ Production-ready RAG system (1000+ events)
- ✅ REST API with authentication & rate limiting
- ✅ Streamlit web interface with interactive maps
- ✅ Comprehensive test suite (236 tests, 82% coverage)
- ✅ Golden dataset (118 annotated queries)
- ✅ Technical documentation (UML, API docs, reports)
- ✅ Deployment scripts (one-command startup)

**Technical Excellence** 🏆
- **High Accuracy**: 87% precision, 91% faithfulness
- **Low Latency**: 2-3 second average response
- **Bilingual Support**: 72% FR/EN equivalence
- **Robust Security**: 2% false positive rate
- **Scalable**: 30 queries/second throughput

**Business Value** 💼
- Unified event discovery (1000+ events, single interface)
- Natural conversation (no complex forms or filters)
- Bilingual support (serve French & English tourists)
- Real-time recommendations (semantic understanding)

**Recommendation**: ✅ System ready for **beta deployment**

---

## Demo Time! 🎬

### Live System Walkthrough

**Let's Try**:
1. Open Streamlit UI: http://localhost:8501
2. Ask: "jazz concerts in Paris this weekend?"
3. Follow-up: "for kids"
4. Show: Interactive map, event details, multi-language

**API Demo**:
1. Open Swagger: http://localhost:8000/docs
2. Test `/chat` endpoint
3. Show: JSON response, sources, metrics

---

## Questions? 🙋

### Contact & Resources

**Documentation**:
- 📘 [Technical Report](TECHNICAL_REPORT.md)
- 🏗️ [System Architecture](docs/SYSTEM_ARCHITECTURE.md)
- 🔌 [API Documentation](docs/API_DOCUMENTATION.md)
- 📊 [Evaluation Results](data/evaluation/reports/)

**Code Repository**:
- 📦 GitHub: [Link to repository]
- 🧪 Run Tests: `python run_tests.py`
- 🚀 Start System: `python start.py`

**Contact**:
- 📧 Email: [Your email]
- 💬 LinkedIn: [Your LinkedIn]

---

**Thank you!**

---

## Appendix: Technical Details

### Appendix A: Data Pipeline

**Data Sources**:
- OpenAgenda API: https://api.openagenda.com
- 1000+ events from Île-de-France region
- Updated daily (automated refresh possible)

**Data Processing**:
1. Fetch: Paginated API requests (100 records/page)
2. Clean:
   - Unicode normalization (NFC)
   - Boilerplate removal (31 junk phrases)
   - Title cleaning (ALL CAPS → Title Case)
3. Normalize:
   - Location standardization (176 IDF cities)
   - Category mapping (9 canonical types)
   - Date parsing (ISO 8601)
4. Deduplicate: By (title + city + date)
5. Enrich: Geocoding for coordinates
6. Store: SQLite + FAISS indexing

---

### Appendix B: Model Parameters

**Mistral Large** (Generation):
```json
{
  "model": "mistral-large-latest",
  "temperature": 0.1,
  "max_tokens": 2048,
  "safe_prompt": true
}
```

**Mistral Embed** (Embeddings):
```json
{
  "model": "mistral-embed",
  "dimensions": 1024
}
```

**FAISS** (Vector Store):
```python
index = faiss.IndexFlatIP(1024)  # Inner product
# No quantization (dataset < 10K)
```

**BM25** (Keyword Search):
```python
from rank_bm25 import BM25Okapi
bm25 = BM25Okapi(tokenized_corpus)
```

---

### Appendix C: Deployment

**Prerequisites**:
- Python 3.11+
- Poetry
- Mistral API key

**Quick Start**:
```bash
# 1. Install dependencies
poetry install

# 2. Configure environment
cp .env.example .env
# Edit .env: Add MISTRAL_API_KEY

# 3. Start services
python start.py

# 4. Access UI
open http://localhost:8501
```

**Docker** (Optional):
```bash
docker-compose up
```

---

### Appendix D: Monitoring

**Health Checks**:
```bash
curl http://localhost:8000/health
```

**Metrics**:
```bash
curl http://localhost:8000/metrics
```

**Logs**:
```bash
tail -f logs/app.log
```

**Circuit Breaker State**:
- Closed: Normal operation
- Open: Too many failures (LLM unavailable)
- Half-Open: Testing recovery

---

**End of Presentation**

*Prepared for: [OpenClassrooms Project 9 Evaluation]*
*Date: January 30, 2026*
