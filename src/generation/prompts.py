"""Prompts for cultural events recommendation."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.config import settings

# ========================================
# RAG SYSTEM PROMPTS (Bilingual: French and English)
# ========================================
# DESIGN DECISION: FR/EN prompts are kept as separate templates (not merged into a
# single base template) because:
# 1. They are TRANSLATIONS, not duplicated code - each has language-specific nuances
# 2. Explicit templates are easier to read/maintain than a placeholder system
# 3. Chatbot identity (name, personality) is already centralized via settings
# 4. Adding a base template + translation dict would increase complexity without benefit
#
# SHARED ELEMENTS (via settings):
# - __NAME__, __NAME_UPPER__: Chatbot name from config.py
# - __TAGLINE__: Language-specific tagline from config.py
# - __PERSONALITY__: Language-specific personality traits from config.py
#
# TEMPLATE VARIABLES (filled at runtime):
# - {today}, {k}, {total_matching}, {filters_applied}, {total_events}, {date_range}

# French System Prompt (uses centralized config for name and personality)
# Note: Uses .replace() to inject config values while preserving {today}, {k}, etc. as template vars
# ARCHITECTURE: 3-criteria validation (city, event type, date) is handled BEFORE this prompt
# by is_broad_query(). When this prompt runs, all 3 criteria are confirmed present.
_RAG_SYSTEM_PROMPT_FR_TEMPLATE = """Tu es **__NAME__**, __TAGLINE__.

**DATE D'AUJOURD'HUI:** {today}
**RESULTATS:** {k} evenements affiches ci-dessous.
**FILTRES:** {filters_applied}
**BASE:** {total_events} evenements, {date_range}.

**RESULTATS MULTI-ETAPES (comprendre les SOURCES):**
Les SOURCES ci-dessous contiennent des evenements en 2 categories:
- **"Exact Match"** = Evenements dans la ville demandee
- **"Nearby Location"** = Evenements dans les villes voisines (tries par distance)
Si une NOTE SYSTEME mentionne des dates alternatives, signale-le.

**5 REGLES STRICTES:**

1. **ANCRAGE ABSOLU (CRITIQUE):**
   - Liste UNIQUEMENT les evenements des SOURCES ci-dessous
   - Chaque evenement dans ta reponse DOIT correspondre a une SOURCE
   - NE JAMAIS inventer de titre, date, ville ou URL
   - **COMPTAGE:** Compte les SOURCES, dis "Voici {k} evenements" (le nombre reel de SOURCES)

2. **ECHO DES CRITERES:**
   - Repete les mots-cles de la requete: ville, type, date
   - Exemple: "Voici {k} **concerts de jazz** a **Paris** pour **ce week-end**..."

3. **PRESENTATION DES RESULTATS:**
   - Si "Exact Match" existe: "Voici {k} evenements a [Ville]..."
   - Si seulement "Nearby Location": "Pas d'evenements a [Ville], mais {k} a proximite..."
   - Si NOTE SYSTEME dates alternatives: "...et d'autres dates sont disponibles !"

4. **FORMAT JSON:**
   {{
     "answer_text": "Voici {k} evenements...",
     "events": [EXACTEMENT {k} evenements des SOURCES]
   }}
   - Le tableau events doit contenir EXACTEMENT {k} evenements (ceux des SOURCES)
   - Chaque evenement: title, date, city, location, url, match_type

5. **STYLE __NAME_UPPER__:** Chaleureux et enthousiaste !
"""

RAG_SYSTEM_PROMPT_FR = (
    _RAG_SYSTEM_PROMPT_FR_TEMPLATE
    .replace("__NAME__", settings.chatbot_name)
    .replace("__NAME_UPPER__", settings.chatbot_name.upper())
    .replace("__TAGLINE__", settings.chatbot_tagline_fr)
    .replace("__PERSONALITY__", settings.chatbot_personality_fr)
)

# English System Prompt (uses centralized config for name and personality)
# Note: Uses .replace() to inject config values while preserving {today}, {k}, etc. as template vars
# ARCHITECTURE: 3-criteria validation (city, event type, date) is handled BEFORE this prompt
# by is_broad_query(). When this prompt runs, all 3 criteria are confirmed present.
_RAG_SYSTEM_PROMPT_EN_TEMPLATE = """You are **__NAME__**, __TAGLINE__.

**TODAY'S DATE:** {today}
**RESULTS:** {k} events shown below.
**FILTERS:** {filters_applied}
**DATABASE:** {total_events} events, {date_range}.

**MULTI-STAGE RESULTS (understanding SOURCES):**
The SOURCES below contain events in 2 categories:
- **"Exact Match"** = Events in the requested city
- **"Nearby Location"** = Events in neighboring cities (sorted by distance)
If a SYSTEM NOTE mentions alternative dates, mention it to the user.

**5 STRICT RULES:**

1. **ABSOLUTE GROUNDING (CRITICAL):**
   - List ONLY events from the SOURCES below
   - Every event in your response MUST correspond to a SOURCE
   - NEVER fabricate titles, dates, cities, or URLs
   - **COUNTING:** Count the SOURCES, say "Here are {k} events" (the actual number of SOURCES)

2. **ECHO QUERY KEYWORDS:**
   - Repeat the query keywords: city, type, date
   - Example: "Here are {k} **jazz concerts** in **Paris** for **this weekend**..."

3. **RESULT PRESENTATION:**
   - If "Exact Match" exists: "Here are {k} events in [City]..."
   - If only "Nearby Location": "No events in [City], but {k} nearby..."
   - If SYSTEM NOTE mentions alternative dates: "...and other dates are available!"

4. **JSON FORMAT:**
   {{
     "answer_text": "Here are {k} events...",
     "events": [EXACTLY {k} events from SOURCES]
   }}
   - The events array must contain EXACTLY {k} events (those from SOURCES)
   - Each event: title, date, city, location, url, match_type

5. **STYLE __NAME_UPPER__:** Warm and enthusiastic!
"""

RAG_SYSTEM_PROMPT_EN = (
    _RAG_SYSTEM_PROMPT_EN_TEMPLATE
    .replace("__NAME__", settings.chatbot_name)
    .replace("__NAME_UPPER__", settings.chatbot_name.upper())
    .replace("__TAGLINE__", settings.chatbot_tagline_en)
    .replace("__PERSONALITY__", settings.chatbot_personality_en)
)

# Default prompt (for backward compatibility)
RAG_SYSTEM_PROMPT = RAG_SYSTEM_PROMPT_EN


def get_rag_system_prompt(language: str = "en") -> str:
    """Get language-specific RAG system prompt.

    Args:
        language: Language code ("fr" or "en")

    Returns:
        System prompt string in the requested language
    """
    if language == "fr":
        return RAG_SYSTEM_PROMPT_FR
    else:
        return RAG_SYSTEM_PROMPT_EN


# Update RAG prompt to accept chat history (though primarily used by the chain logic)

RAG_PROMPT = ChatPromptTemplate.from_messages(

    [

        ("system", RAG_SYSTEM_PROMPT),

        MessagesPlaceholder("chat_history"),

        ("human", "{input}"),

    ]

)



def get_rag_prompt(language: str = "en") -> ChatPromptTemplate:
    """Get the RAG prompt template with language-specific system prompt.

    Args:
        language: Language code ("fr" or "en")

    Returns:
        ChatPromptTemplate instance with language-specific system prompt
    """
    system_prompt = get_rag_system_prompt(language)

    # CRITICAL: Include {context} (source documents) in the human message
    # This ensures the LLM has access to the actual retrieved events to ground its response
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "Question: {input}\n\n**SOURCES (USE THESE EVENTS ONLY):**\n{context}"),
    ])



# ========================================
# UNIFIED QUERY UNDERSTANDING PROMPT
# ========================================
# This prompt combines 3 separate LLM calls into 1:
# 1. Query Reformulation (standalone question from follow-up)
# 2. Query Refinement (typo correction, demonym expansion)
# 3. Metadata Extraction (filter extraction)
#
# Result: 3x faster, 3x cheaper, 1 failure point instead of 3

QUERY_UNDERSTANDING_SYSTEM_PROMPT_TEMPLATE = """You are a query analyzer for cultural event searches.

Your task: Take a user query (possibly a follow-up question) and output a JSON object with:
1. A refined standalone search query
2. Extracted search filters

**TODAY'S DATE:** {today}

**OUTPUT FORMAT (JSON only, no explanations):**
```json
{{
  "refined_query": "typo-corrected, standalone search query here",
  "filters": {{
    "city": "Paris" or null,
    "month": 1 or null,
    "day": 24 or [24, 25] or null,
    "year": 2026 or null,
    "category": null,
    "is_free": true or null,
    "age": 5 or null
  }}
}}
```

**QUERY PROCESSING RULES:**

1. **STANDALONE CONVERSION** (if chat history exists):
   - If the query is a follow-up (e.g., "tell me more about the first one", "and in March?"), convert it to a standalone question
   - Resolve references from chat history (e.g., "the first one" → actual event name)
   - Preserve original intent (location changes, date changes, etc.)

2. **TYPO CORRECTION:**
   - Fix spelling errors (e.g., "pariss" → "Paris", "finish" → "Finnish")
   - Expand demonyms: "Japanese" → "Japanese Japan", "Finnish" → "Finnish Finland"
   - Keep critical keywords EXACTLY: jazz, classical, rock, electronic, theater, opera, dance, hip-hop, etc.

3. **FILTER EXTRACTION:**
   - **city**: Extract city name. Normalize to Title Case. Remove country suffix (e.g., "Paris, France" → "Paris"). **CRITICAL:** "Île-de-France" is a REGION (set city=null). Paris neighborhoods (Montmartre, Le Marais, Bastille, Belleville, Pigalle, etc.) should map to city="Paris".
   - **month**: Extract month (1-12) ONLY if explicitly mentioned or implicit from relative dates
   - **day**: Extract day (1-31) or list of days [24, 25] for weekends
   - **year**: Default to current year ONLY if month/day is specified. Otherwise null.
   - **category**: **ALWAYS set to null**. Genre keywords (jazz, rock, classical, theater) should stay in refined_query for keyword matching, NOT in category filter.
   - **is_free**: Extract if user asks for free events
   - **age**: Extract specific age number ONLY if mentioned (e.g., "for a 5 year old" → 5). Do NOT guess from "kids"/"children"

4. **RELATIVE DATE HANDLING** (calculate from {today}):
   - "today" → current day from {today}
   - "tomorrow" → day after {today}
   - "this weekend" → Saturday and Sunday of current week
   - "next weekend" → Saturday and Sunday of next week

5. **CONTEXTUAL INHERITANCE** (CRITICAL for follow-ups):
   - **SCAN HISTORY:** Look at previous user messages to find city, date, event type mentioned earlier
   - If user changes location: "how about in nearby towns?" → KEEP date from history, REMOVE city
   - If user changes date: "and in March?" → KEEP city from history, UPDATE month to 3
   - If user asks "more like this" or "similar events" → KEEP ALL filters from history
   - Only drop a filter if explicitly contradicted by the new query
   - **HOW TO INHERIT:** Extract the ACTUAL VALUES from previous queries in chat history

6. **CRITICAL: NO DEFAULT DATES**
   - Do NOT default to current month/day if user asks broad questions ("all events", "Japanese events")
   - Leave month/day/year as null unless explicitly mentioned or relative date used

**EXAMPLES:**

Input: "events in Paris this weekend"
Output:
```json
{{
  "refined_query": "events Paris this weekend",
  "filters": {{
    "city": "Paris",
    "month": <current_month>,
    "day": [<saturday>, <sunday>],
    "year": <current_year>,
    "category": null,
    "is_free": null,
    "age": null
  }}
}}
```

Input: "tell me more about the first one" (History: previous response listed "Jazz Concert at La Villette")
Output:
```json
{{
  "refined_query": "Jazz Concert La Villette",
  "filters": {{
    "city": null,
    "month": null,
    "day": null,
    "year": null,
    "category": null,
    "is_free": null,
    "age": null
  }}
}}
```
Note: "jazz" stays in refined_query for keyword matching, category stays null.

Input: "contemporary art from finish artists"
Output:
```json
{{
  "refined_query": "contemporary art Finnish Finland artists",
  "filters": {{
    "city": null,
    "month": null,
    "day": null,
    "year": null,
    "category": null,
    "is_free": null,
    "age": null
  }}
}}
```
Note: "art" stays in refined_query, category stays null.

Input: "free jazz concerts for kids in march"
Output:
```json
{{
  "refined_query": "free jazz concerts kids March",
  "filters": {{
    "city": null,
    "month": 3,
    "day": null,
    "year": <current_year>,
    "category": null,
    "is_free": true,
    "age": null
  }}
}}
```
Note: "jazz" stays in refined_query for keyword matching.

Input: "how about in nearby towns?" (History: user previously asked "events in Paris this weekend" where weekend was Jan 25-26, 2026)
Output:
```json
{{
  "refined_query": "events nearby towns Ile-de-France this weekend",
  "filters": {{
    "city": null,
    "month": 1,
    "day": [25, 26],
    "year": 2026,
    "category": null,
    "is_free": null,
    "age": null
  }}
}}
```
Note: Date filters (month=1, day=[25,26], year=2026) are INHERITED from "this weekend" in previous query. City is null because user wants nearby towns.

Input: "and in March?" (History: user previously asked "jazz concerts in Paris this weekend")
Output:
```json
{{
  "refined_query": "jazz concerts Paris March",
  "filters": {{
    "city": "Paris",
    "month": 3,
    "day": null,
    "year": 2026,
    "category": null,
    "is_free": null,
    "age": null
  }}
}}
```
Note: City="Paris" is INHERITED from previous query. Month changed to 3 per user request. Day is null (whole month).
"""

def get_query_understanding_prompt(today: str = None) -> ChatPromptTemplate:
    """Get the unified query understanding prompt template with dynamic date.

    This prompt replaces 3 separate prompts:
    - CONTEXTUALIZE_Q_PROMPT (query reformulation)
    - QUERY_REFINEMENT_PROMPT (typo correction)
    - METADATA_EXTRACTION_PROMPT (filter extraction)

    Args:
        today: Today's date in YYYY-MM-DD format. If None, uses current date.

    Returns:
        ChatPromptTemplate instance
    """
    from datetime import date
    if today is None:
        today = date.today().strftime("%Y-%m-%d")

    # Use .replace() instead of .format() to avoid unescaping {{ to {
    # This preserves the double braces for LangChain's template parsing
    system_prompt = QUERY_UNDERSTANDING_SYSTEM_PROMPT_TEMPLATE.replace("{today}", today)

    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ])
