# Golden Dataset Review Guide

This guide explains how to review and improve your chatbot using the golden dataset.

## 📋 Overview

The golden dataset workflow helps you:
1. **Test** your chatbot with real queries
2. **Review** what it actually returns vs. what it should return
3. **Provide feedback** to improve future versions
4. **Track quality** over time

## 🔄 Complete Workflow

### Step 1: Run Queries Through Your Chatbot

```bash
# Run ALL queries (may take 5-10 minutes)
python scripts/run_queries_for_review.py

# OR run just first 10 queries for quick testing
python scripts/run_queries_for_review.py --limit 10
```

This creates: `data/evaluation/golden_dataset_review.yaml`

### Step 2: Open the Review File

Open `data/evaluation/golden_dataset_review.yaml` in any text editor (VS Code, Notepad++, etc.)

### Step 3: Review Each Query

For each query, you'll see THREE sections to compare:

```yaml
# ========== QUERY 1/135: Q001 ==========

- id: Q001
  query: "Concerts de jazz à Paris en février"
  language: fr
  complexity: low

  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # 📋 EXPECTED GROUND TRUTH (what SHOULD be returned)
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  expected_ground_truth:
    - event_id: "14551589"
      relevance_score: 1.0
      reason: "Exact match for query criteria"

  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # 🤖 ACTUAL CHATBOT RESPONSE (what WAS returned)
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  actual_response:
    status: SUCCESS
    answer: |
      Voici les concerts de jazz à Paris en février:

      1. Concert de Jazz au Sunset (14551589)
         - Date: 15 février 2026
         - Lieu: Rue des Lombards, Paris

    sources_returned:
      - event_id: "14551589"
        title: "Concert de Jazz au Sunset"
        city: Paris
        score: 0.950
        match_type: Exact Match

  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # 🔍 DATABASE VALIDATION (direct database query)
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  database_query:
    status: SUCCESS
    filters_applied:
      city: Paris
      category: Musique
      month: 2
    total_matching_events: 47

    matching_events_sample:
      - event_id: "14551589"
        title: "Concert de Jazz au Sunset"
        city: Paris
        category: Musique
        date: 2026-02-15
      - event_id: "14551590"
        title: "Jazz Night at Le Duc"
        city: Paris
        category: Musique
        date: 2026-02-22

    interpretation: |
      Database contains 47 events matching the filters.
      Compare this to:
      - Ground truth expected: 1 event
      - Chatbot returned: 1 source

  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  # ✍️ YOUR REVIEW (add your feedback here)
  # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  review:
    status: PENDING  # Change to: APPROVED or NEEDS_IMPROVEMENT

    # Compare actual vs expected:
    comparison_notes: |
      # Did the chatbot return the right events?
      # Was the answer accurate and helpful?
      # Any hallucinations or errors?

    # Issues found:
    issues:
      - # List any problems here

    # Improvements needed:
    improvements:
      - # Suggest improvements here
```

### Step 4: Interpret the Three-Way Comparison

For each query, you now have THREE data points:

1. **Expected Ground Truth**: What you manually annotated as correct
2. **Actual Chatbot Response**: What your RAG system returned
3. **Database Validation**: What actually exists in the database

**Common patterns and what they mean:**

| Pattern | Ground Truth | Chatbot | Database | Issue Type | Action |
|---------|-------------|---------|----------|------------|--------|
| ✅ Perfect | Event A | Event A | Has Event A | None | Approved! |
| ⚠️ Retrieval Failure | Event A | Event B | Has Events A+B | Retrieval/Ranking | Fix search relevance |
| ⚠️ Missing Data | Event A | Nothing | Has Event A | Retrieval broken | Debug vector store |
| ⚠️ Hallucination | Event A | Event B | Only has Event A | Generation issue | Fix LLM grounding |
| ⚠️ Bad Ground Truth | Event A | Event B | Only has Event B | Annotation error | Update ground truth |
| ⚠️ Data Gap | Event A | Nothing | No Event A | Data quality | Add event to database |

**Example 1: Perfect match**
```
Ground Truth: Event 14551589
Chatbot: Event 14551589 (score 0.95)
Database: 47 events including 14551589

✅ APPROVED - Chatbot found the right event!
```

**Example 2: Retrieval failure**
```
Ground Truth: Event 14551589
Chatbot: Event 14551590, 14551591 (NOT 14551589!)
Database: 47 events including ALL three

⚠️ NEEDS_IMPROVEMENT - Database has the right event, but chatbot ranked others higher.
Action: Improve BM25 keyword matching or FAISS embedding quality.
```

**Example 3: Missing event**
```
Ground Truth: Event 14551589
Chatbot: No results
Database: Event 14551589 exists with correct filters

⚠️ NEEDS_IMPROVEMENT - Retrieval completely failed.
Action: Debug vector store index or filter application.
```

**Example 4: Bad ground truth**
```
Ground Truth: Event 14551589
Chatbot: Event 14551590
Database: Only Event 14551590 matches filters (14551589 is in MARCH, not Feb)

⚠️ BAD GROUND TRUTH - Event 14551589 doesn't match query criteria!
Action: Update golden dataset ground truth to Event 14551590.
```

### Step 5: Add Your Review

For each query, edit the `review` section:

**Example 1 - Query works perfectly:**
```yaml
  review:
    status: APPROVED

    comparison_notes: |
      Perfect! Chatbot returned exactly the expected event.
      Answer was clear and in French as expected.
      No hallucinations detected.

    issues:
      - None

    improvements:
      - None needed
```

**Example 2 - Query has issues:**
```yaml
  review:
    status: NEEDS_IMPROVEMENT

    comparison_notes: |
      Chatbot returned event 14551589 correctly, but ALSO returned
      event 99999999 which is in March, NOT February.
      This is a date filtering bug.

    issues:
      - Returned events outside the requested date range
      - Answer included wrong month

    improvements:
      - Fix date filter to be strict (no events outside February)
      - Add validation to ensure all returned events match filters
```

**Example 3 - Query failed:**
```yaml
  review:
    status: NEEDS_IMPROVEMENT

    comparison_notes: |
      ERROR: Chatbot crashed with timeout error.
      Expected to return 3 events but got none.

    issues:
      - Query timed out after 30 seconds
      - No results returned when there should be matches

    improvements:
      - Investigate timeout (too many events in database?)
      - Optimize search query performance
      - Add fallback for timeout scenarios
```

### Step 5: Track Your Progress

As you review:
- **Count APPROVED queries** → These show your chatbot works well
- **Count NEEDS_IMPROVEMENT queries** → These are your priorities to fix
- **Look for patterns** in the issues (e.g., many date filter bugs)

### Step 6: Use Feedback to Improve

Common improvement categories:

| Issue Pattern | Likely Fix |
|--------------|------------|
| Wrong dates returned | Fix date filtering in retrieval |
| Hallucinated event details | Improve grounding prompt |
| Wrong language response | Fix language detection |
| Missing expected events | Improve search relevance |
| Too many irrelevant results | Add reranking or stricter filters |

## 📊 Quick Statistics

After reviewing, you can count:

```bash
# Count approved queries
grep -c "status: APPROVED" data/evaluation/golden_dataset_review.yaml

# Count needs improvement
grep -c "status: NEEDS_IMPROVEMENT" data/evaluation/golden_dataset_review.yaml

# Count pending (not yet reviewed)
grep -c "status: PENDING" data/evaluation/golden_dataset_review.yaml
```

## 🎯 Quality Targets

Good chatbot quality benchmarks:
- **80%+ APPROVED** → Production ready
- **90%+ APPROVED** → Excellent quality
- **95%+ APPROVED** → Outstanding quality

## 🔁 Iterative Improvement Process

1. **Run queries** → Generate review file
2. **Review & annotate** → Add feedback for each query
3. **Identify patterns** → Group similar issues
4. **Fix issues** → Update code based on feedback
5. **Re-run queries** → Generate new review file
6. **Compare** → Did your fixes improve the results?
7. **Repeat** until quality targets met

## 📝 Tips for Effective Review

1. **Be specific** - Don't just say "bad result", explain exactly what's wrong
2. **Note what works** - Positive feedback helps identify what NOT to break
3. **Look for patterns** - If 5 queries fail the same way, it's likely one bug
4. **Prioritize high-value queries** - Fix queries users ask most often first
5. **Test edge cases** - Unusual queries help find bugs early

## 🚀 Advanced: Compare Versions

Save review files with version numbers:
```bash
# Version 1.0
python scripts/run_queries_for_review.py
mv data/evaluation/golden_dataset_review.yaml \
   data/evaluation/reviews/review_v1.0.yaml

# After making improvements, run Version 1.1
python scripts/run_queries_for_review.py
mv data/evaluation/golden_dataset_review.yaml \
   data/evaluation/reviews/review_v1.1.yaml

# Compare to see if you improved
diff reviews/review_v1.0.yaml reviews/review_v1.1.yaml
```

## 📚 Additional Resources

- **Edit golden dataset**: Modify `data/evaluation/golden_dataset.yaml`
- **Add new queries**: Use `scripts/enrich_golden_dataset.py`
- **Export to YAML**: Use `scripts/export_golden_dataset.py`
- **Import from YAML**: Use `scripts/import_golden_dataset.py`

---

**Need help?** Check the main README or review the evaluation scripts in `scripts/`.
