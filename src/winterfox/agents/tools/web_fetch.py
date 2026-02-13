"""
Web page content extraction tool.

Strategies:
1. Try Jina Reader API (fast, clean markdown)
2. Fallback to direct fetch + readability + markdownify
"""

import logging

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify
from readability import Document

logger = logging.getLogger(__name__)


async def web_fetch(url: str, use_jina: bool = True) -> str:
    """
    Fetch clean page content as markdown.

    Args:
        url: URL to fetch
        use_jina: Try Jina Reader first (default: True)

    Returns:
        Clean markdown content
    """
    if use_jina:
        try:
            # Try Jina Reader first (free, fast, clean)
            reader_url = f"https://r.jina.ai/{url}"

            async with httpx.AsyncClient() as client:
                response = await client.get(reader_url, timeout=15.0)

                if response.status_code == 200:
                    logger.info(f"Fetched via Jina Reader: {url}")
                    return response.text

        except Exception as e:
            logger.warning(f"Jina Reader failed for {url}: {e}")

    # Fallback: Direct fetch + readability
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; WinterfoxBot/1.0)"
                },
                timeout=15.0,
            )

            response.raise_for_status()
            html = response.text

        # Extract main content with readability
        doc = Document(html)
        title = doc.title()
        content_html = doc.summary()

        # Convert to markdown
        content_md = markdownify(content_html, heading_style="ATX")

        result = f"# {title}\n\n{content_md}"
        logger.info(f"Fetched via readability: {url}")

        return result

    except Exception as e:
        logger.error(f"Web fetch failed for {url}: {e}")
        return f"Error fetching {url}: {str(e)}"


async def web_fetch_batch(urls: list[str], max_concurrent: int = 5) -> dict[str, str]:
    """
    Fetch multiple URLs concurrently.

    Args:
        urls: List of URLs to fetch
        max_concurrent: Maximum concurrent requests

    Returns:
        Dict mapping URL to content
    """
    import asyncio

    results = {}
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(url: str):
        async with semaphore:
            return url, await web_fetch(url)

    tasks = [fetch_with_semaphore(url) for url in urls]
    completed = await asyncio.gather(*tasks, return_exceptions=True)

    for item in completed:
        if isinstance(item, Exception):
            logger.error(f"Batch fetch error: {item}")
        else:
            url, content = item
            results[url] = content

    return results
