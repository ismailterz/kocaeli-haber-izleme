import asyncio
from services.scraping_pipeline import ScrapingPipeline
from services.database_service import get_database

async def test():
    db = get_database()
    pipeline = ScrapingPipeline(db, max_links=200)
    res = await pipeline.run()
    print("Test Scrape Result:", res)

asyncio.run(test())
