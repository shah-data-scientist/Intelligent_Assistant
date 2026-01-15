# OpenAgenda API Data Analysis & Architecture Recommendations

**Date:** 2026-01-15
**Status:** Phase 1 Complete - Analysis & Recommendations

## Executive Summary

After implementing the data pipeline and analyzing the OpenAgenda API, I can now answer your questions about data availability, geographic/temporal scope, and provide architectural recommendations for optimal system design.

---

## 1. Data Availability Analysis

### API Statistics
- **Total Records Available:** 912,435 cultural events
- **API Source:** [Opendatasoft Public Portal](https://public.opendatasoft.com/explore/dataset/evenements-publics-openagenda/records)
- **API Format:** Opendatasoft v2.1 (REST API with pagination)
- **Geographic Coverage:** All of France (not limited to Paris)

### Date Range (Sample of 100 events)
- **Earliest Event:** 2017-10-13
- **Latest Event:** 2032-01-01
- **Date Span:** 5,192 days (~14 years)
- **Past Events:** 99% (in sampled data)
- **Upcoming Events:** 1% (in sampled data)

**Key Finding:** The API contains primarily **historical data** with limited upcoming events in the current sample. The dataset spans events from 2017 to 2032, but most are past events.

### Geographic Distribution (Sample of 100 events)
**Paris Events:** Only **2 out of 100** (2%) in the sample
**Top Cities:**
- Tourcoing: 5 events
- Toulouse, Nantes, Berlin: 3 events each
- Marseille, Villeurbanne, Paris: 2 events each

**Key Finding:** Paris events are a **small subset** of the total dataset. Geographic filtering is **essential** to focus on Paris-specific events.

---

## 2. Was Geographic/Temporal Scope Implemented?

### ✅ Geographic Filtering: YES

```python
# Implemented in src/data/processor.py
def filter_paris_events(events: list[Event]) -> list[Event]:
    """Filter events to only include Paris events."""
    paris_events = [
        event for event in events
        if event.location
        and event.location.city
        and "paris" in event.location.city.lower()
    ]
    return paris_events
```

**Capability:** Filters events by checking if city name contains "Paris" (case-insensitive).

### ✅ Temporal Filtering: YES

```python
# Implemented in src/data/processor.py
def filter_by_date_range(
    events: list[Event],
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> list[Event]:
    """Filter events by date range."""
    # Filters events within specified date window
```

**Capability:** Filters events within any specified date range (e.g., next 12 months).

### ⚠️ Gap: Pipeline Integration

These filters are **utility methods** but are **NOT automatically applied** in a pipeline yet. To fully implement the "Paris events within 1-year window" requirement, we need to:
1. Create a data ingestion pipeline that fetches events
2. **Automatically apply** Paris + date range filters
3. Store filtered results for embedding/indexing

---

## 3. Architectural Recommendation: Local Database + Incremental Sync

### Your Proposal: Local Storage with API Sync

> "Store all events in a local database, then whenever a new user request is made through the chatbot, perform a check against the external API to see whether new events are available. If new events are found, import them into the local database and go through the usual processing pipeline."

### My Assessment: **STRONGLY RECOMMENDED** ✅

This approach is **not just wiser—it's essential** for a RAG system. Here's why:

---

## Why Local Database + Sync is Essential

### 1. **RAG System Requirements**

A RAG (Retrieval-Augmented Generation) system with FAISS **requires**:
- **Pre-computed embeddings:** You cannot embed events in real-time during queries (too slow)
- **Pre-built vector index:** FAISS index must be constructed beforehand
- **Fast retrieval:** Vector similarity search is fast only if the index is pre-loaded

**Conclusion:** You **cannot** do real-time API fetching + embedding + indexing on each query. It's architecturally impossible to meet the <2 second latency target.

### 2. **Performance Comparison**

| Approach | Query Latency | Feasibility |
|----------|--------------|-------------|
| **Direct API (no local storage)** | 5-30 seconds | ❌ Impossible for RAG |
| - Fetch events from API | ~1-2 seconds | |
| - Process/clean data | ~0.5 seconds | |
| - Generate embeddings (Mistral API) | ~2-5 seconds | |
| - Build FAISS index | ~1-3 seconds | |
| - Perform retrieval | ~0.1 seconds | |
| - Generate response | ~1-2 seconds | |
| **Local DB + Pre-computed Embeddings** | <2 seconds | ✅ Achievable |
| - Load pre-built FAISS index | ~0.05 seconds (cached) | |
| - Perform retrieval | ~0.1 seconds | |
| - Generate response | ~1-2 seconds | |

### 3. **Cost Optimization**

**Embeddings Cost:**
- Direct approach: Embed events on **every query** → High cost
- Local approach: Embed events **once** when ingested → Low cost

**Example:** For 1,000 events with 100 queries:
- Direct: 1,000 × 100 = **100,000 embedding calls**
- Local: 1,000 × 1 = **1,000 embedding calls** (99% cost savings)

### 4. **Data Freshness Trade-off**

**Direct API (real-time):**
- ✅ Always fresh data
- ❌ Too slow for RAG
- ❌ Expensive

**Local DB + Periodic Sync:**
- ✅ Fast retrieval
- ✅ Cost-effective
- ⚠️ Slightly stale (depends on sync frequency)

For cultural events, a sync frequency of **every 6-24 hours** is perfectly acceptable.

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Ingestion Pipeline (Periodic)               │
│                                                               │
│  OpenAgenda API → Process → Filter → Embed → FAISS Index   │
│                    │         │        │         │            │
│                    │         │        │         ↓            │
│                    │         │        │    Local Vector DB   │
│                    │         │        │    (FAISS + Metadata)│
│                    │         │        ↓                      │
│                    │         │    Mistral Embeddings        │
│                    │         │    (Computed Once)           │
│                    │         ↓                               │
│                    │    Paris + 1-Year Filter               │
│                    ↓                                          │
│               Clean & Normalize                              │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ (Runs every 6-24 hours)
                           │
┌─────────────────────────────────────────────────────────────┐
│                   Query Pipeline (Real-time)                 │
│                                                               │
│  User Query → Load Index → Retrieve → Generate → Response  │
│               (Fast)       (Fast)     (LLM)      (<2s)       │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Strategy

**Phase 1: Data Storage Layer** (Add to existing pipeline)
- Choose storage: SQLite (simple) or PostgreSQL (production-ready)
- Schema: Store Event objects + embeddings + FAISS metadata
- Add deduplication logic (prevent duplicate event IDs)

**Phase 2: Incremental Update Logic**
- Track last sync timestamp
- On each sync:
  1. Fetch events from API (with date filter: now → +1 year)
  2. Check against existing event IDs in DB
  3. **Insert only new events**
  4. Delete events older than 1 year (cleanup)
  5. Rebuild FAISS index with updated events

**Phase 3: Intelligent Sync Strategy**
```python
# Pseudo-code
def sync_events():
    last_sync = get_last_sync_time()
    now = datetime.now()

    # Fetch upcoming Paris events (next 12 months)
    new_events = fetch_paris_events(
        start_date=now,
        end_date=now + timedelta(days=365)
    )

    # Deduplicate
    existing_ids = get_existing_event_ids()
    new_events = [e for e in new_events if e.event_id not in existing_ids]

    # Process + Embed + Store
    for event in new_events:
        embedding = generate_embedding(event.to_text())
        store_event(event, embedding)

    # Rebuild FAISS index
    rebuild_faiss_index()

    update_last_sync_time(now)
```

---

## Implementation Gaps & Next Steps

### Current Implementation Status

✅ **Implemented:**
- OpenAgenda API client with pagination
- Event data models (Event, EventLocation)
- Data processing & normalization
- Geographic filtering (Paris)
- Temporal filtering (date range)
- Comprehensive test suite

⚠️ **Missing (Required for RAG):**
1. **Local database layer** (SQLite/PostgreSQL)
2. **Mistral embeddings integration**
3. **FAISS index builder**
4. **Incremental sync pipeline**
5. **Automated periodic sync** (cron job / scheduler)

### Recommended Next Steps

**Immediate Priority:**
1. **Add database layer** (Phase 1.5)
   - Create `src/data/storage.py` with SQLite backend
   - Add event CRUD operations
   - Add deduplication logic

2. **Continue with Phase 2** (Vector Store & Embeddings)
   - Implement Mistral embeddings
   - Build FAISS indexing
   - Connect storage → embeddings → FAISS

3. **Create ingestion pipeline script** (Phase 1.5)
   - `scripts/ingest_events.py` - full pipeline
   - Fetch → Filter (Paris + 1 year) → Store → Embed → Index

4. **Add sync scheduler** (Phase 6)
   - Configurable sync frequency (default: every 12 hours)
   - Background task or cron job

---

## Summary

**Your Questions Answered:**

1. **How many records?** 912,435 total in API; ~2% are Paris events in sample data
2. **Date range?** 2017-2032, but mostly historical (99% past events in sample)
3. **Was Paris + 1-year filter implemented?** Yes, as utility functions; not yet in automated pipeline
4. **Is local database approach better?** **Absolutely yes** - essential for RAG performance, cost optimization, and latency targets

**Architecture Verdict:**
- ✅ **Local database + incremental sync** is the **only viable approach** for a production RAG system
- ❌ **Direct API queries** would make <2s latency impossible
- 🎯 **Sync frequency:** Every 6-24 hours is optimal for cultural events

---

## References

- [Opendatasoft Public Events API](https://public.opendatasoft.com/explore/dataset/evenements-publics-openagenda/api/)
- [Data hub - OpenAgenda](https://data.opendatasoft.com/explore/dataset/evenements-publics-openagenda@public/)
- [Île-de-France Open Data - Public Events](https://data.iledefrance.fr/explore/dataset/evenements-publics-cibul/api/)
