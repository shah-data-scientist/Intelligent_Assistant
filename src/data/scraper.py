"""Web scraper for event content enrichment."""

import logging
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class EventScraper:
    """Scraper to fetch and extract text content from event URLs."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    async def scrape_url(self, url: str) -> str | None:
        """Fetch URL and extract main text content.

        Args:
            url: The URL to scrape

        Returns:
            Extracted text or None if failed
        """
        if not url:
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Remove scripts and styles
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()

                # Extract text
                text = soup.get_text(separator="\n")
                
                # Clean whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = "\n".join(chunk for chunk in chunks if chunk)
                
                # Limit length to avoid massive context
                return text[:2000] 

        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
            return None
