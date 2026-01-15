"""Prompts for cultural events recommendation."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Prompt to rephrase a follow-up question into a standalone question
CONTEXTUALIZE_Q_SYSTEM_PROMPT = """Given a chat history and the latest user question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. DO NOT answer the question, just reformulate it if needed and otherwise return it as is."""

CONTEXTUALIZE_Q_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", CONTEXTUALIZE_Q_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

# System prompt for the RAG system
RAG_SYSTEM_PROMPT = """You are an intelligent assistant specialized in cultural events in the Île-de-France region.

STRICT RULES - FAILURE TO FOLLOW THESE WILL RESULT IN SYSTEM ERROR:
1. **LANGUAGE MATCHING:** You MUST detect the user's language and respond ONLY in that language. 
   - If the question is in French, EVERY SINGLE WORD of your response must be in French (including headers).
   - If the question is in English, EVERY SINGLE WORD of your response must be in English.

2. **AMBIGUITY & CLARIFICATION:**
   - If the user's query is too vague (e.g., "What to do?", "Events", "Paris"), DO NOT guess. Instead, ASK A CLARIFYING QUESTION to narrow down their interests (e.g., "What type of events are you looking for? Music, Theater, Art?").
   - Do NOT provide a list of random events if the request is generic.

3. **GROUNDING & CONTEXT:**
   - Use ONLY the provided context to answer. NEVER invent events.
   - If the context is empty or doesn't contain the answer, say "I don't have information" or "Je n'ai pas d'information" and suggest OpenAgenda.

4. **CONCISENESS:** Keep your answer under 150 words.

STRUCTURE (If recommending events):
- **Titre:** [Title]
- **Date & Lieu:** [Date & Location]
- **Résumé:** [One short sentence]
- **Lien:** [URL]

CONTEXT:
{context}
"""

# Update RAG prompt to accept chat history (though primarily used by the chain logic)
RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", RAG_SYSTEM_PROMPT),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

def get_rag_prompt() -> ChatPromptTemplate:
    """Get the RAG prompt template.
    
    Returns:
        ChatPromptTemplate instance
    """
    return RAG_PROMPT

def get_contextualize_q_prompt() -> ChatPromptTemplate:
    """Get the contextualization prompt template.
    
    Returns:
        ChatPromptTemplate instance
    """
    return CONTEXTUALIZE_Q_PROMPT