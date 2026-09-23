import sys
import asyncio
from typing import Optional, Dict, Any

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

TARGET_URL = "https://www.scstatehouse.gov/code/t44c115.php"

async def _crawl_internal() -> Dict[str, Any]:
    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        excluded_tags=["nav", "header", "footer", "script", "style"]
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=TARGET_URL, config=config)

        if result.success:
            return {
                "success": True,
                "url": TARGET_URL,
                "markdown": result.markdown,
                "error": None
            }
        else:
            return {
                "success": False,
                "url": TARGET_URL,
                "markdown": None,
                "error": result.error_message
            }

def _run_in_isolated_thread() -> Dict[str, Any]:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    return asyncio.run(_crawl_internal())

async def crawl_url() -> Dict[str, Any]:
    return await asyncio.to_thread(_run_in_isolated_thread)

async def main():
    res = await crawl_url()
    if res["success"]:
        print("=== SCRAPED REGULATION CONTENT ===\n")
        print(res["markdown"])
    else:
        print(f"Failed to fetch content: {res['error']}")

if __name__ == "__main__":
    asyncio.run(main())