"""Debug RAGChain latency and errors."""

import logging
import time
from src.retrieval.chain import RAGChain

# Enable debug logging for httpx to see API calls
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)
logging.getLogger("httpcore").setLevel(logging.DEBUG)

def debug_chain():
    print("Initializing RAGChain...")
    start = time.time()
    chain = RAGChain()
    print(f"Initialization took {time.time() - start:.2f}s")
    
    question = "Are there any jazz concerts in Paris?"
    print(f"\nQuerying: {question}")
    
    start = time.time()
    try:
        response = chain.query(question)
        print("\nResponse received:")
        print(response)
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        print(f"Total query time: {time.time() - start:.2f}s")

if __name__ == "__main__":
    debug_chain()

