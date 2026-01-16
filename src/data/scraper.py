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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
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
                
                # Remove only structural clutter
                for script in soup(["script", "style", "noscript", "iframe"]):
                    script.decompose()

                # Try to find the main content area
                # OpenAgenda: often has specific classes
                content_node = (
                    soup.find(class_="oa-event-description") or
                    soup.find(class_="event-description") or
                    soup.find("main") or
                    soup.find("article") or
                    soup.find(id="main") or
                    soup.body
                )

                if not content_node:
                    return None

                # Extract text
                text = content_node.get_text(separator="\n")
                
                # Clean text
                lines = []
                for line in text.splitlines():
                    clean_line = line.strip()
                    # Filter out cookie noise
                    if "cookie" in clean_line.lower() or "matomo" in clean_line.lower():
                        continue
                    if clean_line:
                        lines.append(clean_line)
                
                text = "\n".join(lines)
                
                return text[:10000] 

        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
            return None
