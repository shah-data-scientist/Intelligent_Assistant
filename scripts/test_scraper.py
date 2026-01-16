"""Test scraper on a specific URL."""

import asyncio
from src.data.scraper import EventScraper

async def test():
    scraper = EventScraper()
    url = "https://openagenda.com/catalogue-structures-accueil-hebergement/events/fiap-jean-monnet"
    print(f"Scraping {url}...")
    content = await scraper.scrape_url(url)
    print("\n--- RESULT ---")
    print(content)
    print("\n--- END RESULT ---")

if __name__ == "__main__":
    asyncio.run(test())

