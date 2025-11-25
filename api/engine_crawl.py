"""
Crawling engine for AI Visibility MVP
Handles page discovery and fetching

Enhancements:
- Retry with exponential backoff for HTTP fetches
- Optional concurrency helpers for bulk fetching
- TTL cache for robots.txt and sitemap.xml to reduce load
"""

import os
import random
import time
from typing import Dict, List, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Simple in-memory cache for special endpoints (robots/sitemap)
_SPECIAL_CACHE: Dict[str, Tuple[float, str]] = {}


def _is_special_cached_url(url: str) -> bool:
    """Return True if the URL is a robots.txt or sitemap.xml we should cache."""
    try:
        parsed = urlparse(url)
        path = (parsed.path or "").lower()
        return (
            path.endswith("/robots.txt")
            or path.endswith("/sitemap.xml")
            or path == "/robots.txt"
            or path == "/sitemap.xml"
        )
    except Exception:
        return False


def fetch(url: str) -> Tuple[str, str]:
    """
    Fetches HTML content from a URL.

    Args:
        url: Target URL to fetch

    Returns:
        Tuple of (url, html_content) or (url, '') on error
    """
    # TTL cache for robots/sitemap
    if _is_special_cached_url(url):
        ttl = int(os.getenv("ROBOTS_SITEMAP_CACHE_TTL_SECONDS", "86400"))  # default 24h
        cached = _SPECIAL_CACHE.get(url)
        now = time.time()
        if cached and (now - cached[0]) < ttl:
            return (url, cached[1])

    retry_count = max(1, int(os.getenv("FETCH_RETRY_COUNT", "3")))
    backoff_base = max(0.0, float(os.getenv("FETCH_BACKOFF_SECONDS", "0.5")))

    for attempt in range(retry_count):
        try:
            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            # Retry on transient server errors
            if response.status_code >= 500:
                raise RuntimeError(f"server error {response.status_code}")

            if response.status_code == 200:
                html = response.text
                if _is_special_cached_url(url):
                    _SPECIAL_CACHE[url] = (time.time(), html)
                return (url, html)
            # Non-200 and not retriable
            return (url, "")
        except Exception:
            # Final attempt: break and return empty
            if attempt == retry_count - 1:
                break
            # Exponential backoff with jitter
            delay = backoff_base * (2**attempt) + random.uniform(0, 0.1)
            try:
                time.sleep(delay)
            except Exception:
                pass

    return (url, "")


def discover_pages(url: str, max_pages: int | None = None) -> List[str]:
    """
    Discovers pages to audit from a website.

    Args:
        url: Homepage URL
        max_pages: Maximum number of pages to discover (default from env CRAWL_MAX_PAGES or 5)

    Returns:
        List of up to max_pages URLs to audit
    """
    # Get max_pages from parameter, env, or default to 5
    if max_pages is None:
        max_pages = int(os.getenv("CRAWL_MAX_PAGES", "5"))
    max_pages = max(1, max_pages)  # Ensure at least 1 page
    # Parse and normalize input URL
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)

    base_domain = parsed.netloc
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Start with homepage
    pages = [url]
    discovered_urls = set([_normalize_url(url)])

    # Try sitemap.xml first
    sitemap_url = f"{base_url}/sitemap.xml"
    _, sitemap_html = fetch(sitemap_url)

    if sitemap_html:
        try:
            soup = BeautifulSoup(sitemap_html, "lxml-xml")
            locs = soup.find_all("loc")
            # Take up to (max_pages - 1) from sitemap since we already have homepage
            sitemap_limit = min(len(locs), max_pages - 1)
            for loc in locs[:sitemap_limit]:
                page_url = loc.get_text().strip()
                normalized = _normalize_url(page_url)
                if normalized not in discovered_urls and urlparse(page_url).netloc == base_domain:
                    pages.append(page_url)
                    discovered_urls.add(normalized)
                    if len(pages) >= max_pages:
                        break
        except Exception:
            pass

    # If still need more pages, crawl homepage links
    if len(pages) < max_pages:
        _, homepage_html = fetch(url)
        if homepage_html:
            try:
                soup = BeautifulSoup(homepage_html, "html.parser")
                links = soup.find_all("a", href=True)

                # Categorize by depth
                urls_by_depth = {0: [], 1: [], 2: [], 3: []}

                for link in links:
                    href = link["href"]
                    absolute_url = urljoin(base_url, href)

                    # Filter invalid URLs
                    parsed_link = urlparse(absolute_url)
                    if (
                        parsed_link.netloc != base_domain
                        or parsed_link.scheme not in ["http", "https"]
                        or absolute_url.startswith("mailto:")
                        or absolute_url.startswith("javascript:")
                    ):
                        continue

                    # Normalize and deduplicate
                    normalized = _normalize_url(absolute_url)
                    if normalized in discovered_urls:
                        continue

                    # Calculate path depth
                    path = parsed_link.path.strip("/")
                    depth = len(path.split("/")) if path else 0
                    depth_key = min(depth, 3)

                    urls_by_depth[depth_key].append(absolute_url)

                # Select URLs with diversity
                for depth in [0, 1, 2, 3]:
                    for page_url in urls_by_depth[depth]:
                        normalized = _normalize_url(page_url)
                        if normalized not in discovered_urls:
                            pages.append(page_url)
                            discovered_urls.add(normalized)
                            if len(pages) >= max_pages:
                                break
                    if len(pages) >= max_pages:
                        break
            except Exception:
                pass

    # Cap at max_pages and return
    return pages[:max_pages]


def fetch_many(urls: List[str], max_workers: int | None = None) -> List[Tuple[str, str]]:
    """
    Fetch multiple URLs concurrently using thread pool.

    Args:
        urls: List of URLs to fetch
        max_workers: Optional parallelism (default from CRAWL_MAX_WORKERS env, fallback 4)

    Returns:
        List of (url, html) tuples in the same order as input
    """
    if not urls:
        return []

    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
    except Exception:
        # Fallback to sequential if concurrency primitives unavailable
        return [fetch(u) for u in urls]

    workers = (
        max_workers
        if isinstance(max_workers, int) and max_workers > 0
        else int(os.getenv("CRAWL_MAX_WORKERS", "4") or 4)
    )
    # Ensure at least 1 worker
    workers = max(1, workers)

    out: Dict[str, Tuple[str, str]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_url = {executor.submit(fetch, u): u for u in urls}
        for future in as_completed(future_to_url):
            u = future_to_url[future]
            try:
                out[u] = future.result()
            except Exception:
                out[u] = (u, "")

    # Preserve original order
    return [out.get(u, (u, "")) for u in urls]


def _normalize_url(url: str) -> str:
    """Normalizes URL for comparison."""
    parsed = urlparse(url)
    # Remove fragment and trailing slash
    path = parsed.path.rstrip("/")
    normalized = f"{parsed.scheme}://{parsed.netloc.lower()}{path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized
