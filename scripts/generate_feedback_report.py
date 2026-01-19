"""
Automated Feedback Analysis & Remediation Reporting Tool.

This script:
1. Connects to the SQLite database.
2. Retrieves all negative feedback with conversation context.
3. Sends the data to the LLM to generate a Root Cause Analysis (RCA) and Remediation Plan.
4. Saves the report to 'docs/FEEDBACK_REPORT.md'.
"""

import sqlite3
import logging
import sys
from datetime import datetime
from pathlib import Path

# Ensure src is in path
sys.path.append(str(Path(__file__).parent.parent))

from src.generation.llm import MistralLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from src.config import settings
DB_PATH = settings.chat_db_path
REPORT_PATH = "docs/FEEDBACK_REPORT_LATEST.md"

def get_feedback_context(db_path: str, limit: int = 20):
    """Fetch negative feedback and preceding user queries."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Get negative feedbacks and the assistant's message
    query = """
    SELECT 
        f.id,
        f.comment,
        f.timestamp,
        c.session_id,
        c.content as assistant_response,
        c.timestamp as msg_timestamp
    FROM feedbacks f
    JOIN conversations c ON f.message_id = c.id
    WHERE f.is_positive = 0
    ORDER BY f.timestamp DESC
    LIMIT ?
    """
    
    cursor.execute(query, (limit,))
    rows = cursor.fetchall()
    
    feedback_data = []
    
    for row in rows:
        f_id, comment, f_time, session_id, bot_response, msg_time = row
        
        # 2. Find the immediate preceding user message for context
        user_query_sql = """
        SELECT content 
        FROM conversations 
        WHERE session_id = ? 
          AND role = 'user' 
          AND timestamp < ?
        ORDER BY timestamp DESC 
        LIMIT 1
        """
        cursor.execute(user_query_sql, (session_id, msg_time))
        user_row = cursor.fetchone()
        user_query = user_row[0] if user_row else "[Unknown User Query]"
        
        feedback_data.append({
            "feedback_id": f_id,
            "date": f_time,
            "user_query": user_query,
            "bot_response": bot_response,
            "user_feedback": comment
        })
        
    conn.close()
    return feedback_data

def generate_report(feedback_data):
    """Use LLM to generate a strategic report."""
    if not feedback_data:
        logger.warning("No negative feedback found to analyze.")
        return "No negative feedback found in the database."

    # Format data for the Prompt
    context_str = ""
    for item in feedback_data:
        context_str += f"""
---
[Feedback ID: {item['feedback_id']}] Date: {item['date']}
USER QUERY: {item['user_query']}
BOT RESPONSE: {item['bot_response']}
NEGATIVE FEEDBACK: {item['user_feedback']}
"""

    # Analysis Prompt
    system_prompt = """You are a Lead QA Engineer and Product Manager for an AI Assistant.
Your goal is to analyze user feedback logs to improve the system.

Identify patterns in the provided feedback logs.
Output a structured Markdown report with the following sections:

# 1. Executive Summary
Brief overview of the main issues (e.g., "30% of issues are related to hallucinations").

# 2. Root Cause Analysis
Group the feedback into categories (e.g., Tone, Data Coverage, Logic, Hallucination).
For each category, explain *why* it is happening based on the logs.

# 3. Remediation Plan
For each identified root cause, propose specific, technical remediation steps.
(e.g., "Update system prompt to include X", "Ingest more data for Y", "Fix retrieval chain logic").

# 4. Critical Feedback List
Briefly list the most critical feedback items that need immediate attention.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Here are the recent negative feedback logs:\n{context}")
    ])

    logger.info("Initializing LLM for analysis...")
    llm = MistralLLM().llm
    chain = prompt | llm | StrOutputParser()
    
    logger.info("Generating report...")
    return chain.invoke({"context": context_str})

def main():
    logger.info(f"Connecting to database at {DB_PATH}...")
    try:
        data = get_feedback_context(DB_PATH)
        logger.info(f"Retrieved {len(data)} feedback items.")
        
        report_content = generate_report(data)
        
        # Save report
        output_file = Path(REPORT_PATH)
        output_file.parent.mkdir(exist_ok=True)
        output_file.write_text(report_content, encoding="utf-8")
        
        logger.info(f"Report successfully saved to: {output_file.absolute()}")
        print("\n" + "="*50)
        print("FEEDBACK ANALYSIS COMPLETE")
        print("="*50)
        print(f"Report saved to: {REPORT_PATH}")
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}", exc_info=True)

if __name__ == "__main__":
    main()
