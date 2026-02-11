"""Website crawler with robots.txt compliance and rate limiting."""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Patterns that suggest a page has updates / news content
NEWS_URL_PATTERNS = re.compile(
    r"(blog|news|press|release|announce|update|changelog|what.?s.?new|article|post)",
    re.IGNORECASE,
)

# Maximum pages to crawl per analysis
MAX_PAGES = 50
# Maximum depth from seed URL
MAX_DEPTH = 3
# Delay between requests to the same domain (seconds)
REQUEST_DELAY = 0.5
# Request timeout
REQUEST_TIMEOUT = 15.0


class RobotsChecker:
    """Check robots.txt rules for a domain."""

    def __init__(self) -> None:
        self._cache: dict[str, Optional[str]] = {}

    async def fetch_robots(self, client: httpx.AsyncClient, base_url: str) -> Optional[str]:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        if robots_url in self._cache:
            return self._cache[robots_url]
        try:
            resp = await client.get(robots_url, timeout=10.0)
            if resp.status_code == 200:
                self._cache[robots_url] = resp.text
                return resp.text
        except Exception:
            pass
        self._cache[robots_url] = None
        return None

    def is_allowed(self, robots_txt: Optional[str], url: str, user_agent: str = "*") -> bool:
        if robots_txt is None:
            return True
        path = urlparse(url).path
        # Simple robots.txt parser
        current_agent = None
        disallowed: list[str] = []
        for line in robots_txt.splitlines():
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            if line.lower().startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip()
            elif line.lower().startswith("disallow:") and current_agent in (user_agent, "*"):
                rule = line.split(":", 1)[1].strip()
                if rule:
                    disallowed.append(rule)
        for rule in disallowed:
            if path.startswith(rule):
                return False
        return True


class CrawledPage:
    """Represents a single crawled page with its extracted data."""

    def __init__(
        self,
        url: str,
        status_code: int,
        html: str = "",
        headers: Optional[dict] = None,
        error: Optional[str] = None,
    ):
        self.url = url
        self.status_code = status_code
        self.html = html
        self.headers = headers or {}
        self.error = error
        self.soup: Optional[BeautifulSoup] = None
        self.title: str = ""
        self.text_content: str = ""
        self.meta: dict[str, str] = {}
        self.links: list[str] = []
        self.publication_date: Optional[str] = None
        self.last_modified: Optional[str] = None
        self.structured_data: list[dict] = []
        self.depth: int = 0

        if html:
            self._parse()

    def _parse(self) -> None:
        try:
            self.soup = BeautifulSoup(self.html, "lxml")
        except Exception:
            return

        # Title
        title_tag = self.soup.find("title")
        self.title = title_tag.get_text(strip=True) if title_tag else ""

        # Meta tags (extract before decomposing anything)
        for meta in self.soup.find_all("meta"):
            name = meta.get("name", "") or meta.get("property", "")
            content = meta.get("content", "")
            if name and content:
                self.meta[name.lower()] = content

        # Publication date from meta
        date_fields = [
            "article:published_time",
            "og:updated_time",
            "date",
            "pubdate",
            "publishdate",
            "dc.date",
            "dc.date.issued",
            "article:modified_time",
        ]
        for field in date_fields:
            if field in self.meta:
                self.publication_date = self.meta[field]
                break

        # Last-Modified header
        self.last_modified = self.headers.get("last-modified")

        # Links (extract before decomposing nav/header)
        parsed_base = urlparse(self.url)
        for a in self.soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(self.url, href)
            parsed = urlparse(full_url)
            if parsed.netloc == parsed_base.netloc and parsed.scheme in ("http", "https"):
                clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if clean not in self.links:
                    self.links.append(clean)

        # Structured data (JSON-LD) — extract BEFORE decomposing script tags
        import json as _json
        for script in self.soup.find_all("script", type="application/ld+json"):
            try:
                raw = script.string or ""
                data = _json.loads(raw)
                if isinstance(data, list):
                    self.structured_data.extend(data)
                elif isinstance(data, dict):
                    self.structured_data.append(data)
            except Exception:
                pass

        # Text content — decompose non-content tags AFTER all other extraction
        for tag in self.soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        self.text_content = self.soup.get_text(separator=" ", strip=True)[:5000]


class WebsiteCrawler:
    """Async website crawler with robots.txt compliance."""

    USER_AGENT = "WebsiteChangeAnalyzer/1.0 (research bot)"

    def __init__(self, base_url: str, sections: list[str] | None = None, max_pages: int = MAX_PAGES):
        self.base_url = base_url
        self.sections = sections or []
        self.max_pages = max_pages
        self.parsed_base = urlparse(base_url)
        self.domain = f"{self.parsed_base.scheme}://{self.parsed_base.netloc}"
        self.visited: set[str] = set()
        self.pages: list[CrawledPage] = []
        self.robots_checker = RobotsChecker()
        self.robots_txt: Optional[str] = None
        self.rss_feeds: list[dict] = []
        self.sitemap_entries: list[dict] = []
        self._last_request_time: float = 0

    async def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < REQUEST_DELAY:
            await asyncio.sleep(REQUEST_DELAY - elapsed)
        self._last_request_time = time.monotonic()

    def _should_prioritize(self, url: str) -> bool:
        """Check if URL likely contains news/update content."""
        return bool(NEWS_URL_PATTERNS.search(url))

    def _build_seed_urls(self) -> list[str]:
        """Build initial URL list from base URL and sections."""
        seeds = [self.base_url]
        for section in self.sections:
            section = section.strip("/")
            seeds.append(f"{self.domain}/{section}")
        # Common update pages
        common_paths = [
            "/blog", "/news", "/changelog", "/updates",
            "/press", "/announcements", "/whats-new",
            "/releases", "/sitemap.xml", "/feed", "/rss",
        ]
        for path in common_paths:
            seeds.append(f"{self.domain}{path}")
        return seeds

    async def _fetch_page(self, client: httpx.AsyncClient, url: str) -> Optional[CrawledPage]:
        """Fetch a single page."""
        if url in self.visited:
            return None
        if not self.robots_checker.is_allowed(self.robots_txt, url):
            logger.info(f"Blocked by robots.txt: {url}")
            return None

        self.visited.add(url)
        await self._rate_limit()

        try:
            resp = await client.get(
                url,
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
            )
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "text/xml" not in content_type and "application/xml" not in content_type and "application/rss" not in content_type and "application/atom" not in content_type:
                return None

            page = CrawledPage(
                url=str(resp.url),
                status_code=resp.status_code,
                html=resp.text,
                headers=dict(resp.headers),
            )
            return page
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return CrawledPage(url=url, status_code=0, error=str(e))

    async def _parse_sitemap(self, client: httpx.AsyncClient) -> None:
        """Parse sitemap.xml for lastmod dates."""
        sitemap_url = f"{self.domain}/sitemap.xml"
        try:
            await self._rate_limit()
            resp = await client.get(sitemap_url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml-xml")
                for url_tag in soup.find_all("url"):
                    loc = url_tag.find("loc")
                    lastmod = url_tag.find("lastmod")
                    if loc:
                        entry = {"url": loc.get_text(strip=True)}
                        if lastmod:
                            entry["lastmod"] = lastmod.get_text(strip=True)
                        self.sitemap_entries.append(entry)
        except Exception as e:
            logger.info(f"Could not parse sitemap: {e}")

    async def _parse_rss_feeds(self, client: httpx.AsyncClient) -> None:
        """Find and parse RSS/Atom feeds."""
        feed_urls = [
            f"{self.domain}/feed",
            f"{self.domain}/rss",
            f"{self.domain}/feed.xml",
            f"{self.domain}/rss.xml",
            f"{self.domain}/atom.xml",
            f"{self.domain}/blog/feed",
            f"{self.domain}/blog/rss",
        ]

        # Also check link tags in the homepage
        homepage = next((p for p in self.pages if p.url.rstrip("/") == self.base_url.rstrip("/")), None)
        if homepage and homepage.soup:
            for link in homepage.soup.find_all("link", type=re.compile(r"(rss|atom)", re.I)):
                href = link.get("href")
                if href:
                    feed_urls.append(urljoin(self.base_url, href))

        for feed_url in feed_urls[:5]:
            try:
                await self._rate_limit()
                resp = await client.get(feed_url, timeout=REQUEST_TIMEOUT, follow_redirects=True)
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.text)
                    for entry in feed.entries[:20]:
                        item = {
                            "title": getattr(entry, "title", ""),
                            "link": getattr(entry, "link", ""),
                            "published": getattr(entry, "published", ""),
                            "summary": getattr(entry, "summary", "")[:500],
                        }
                        if item["title"] or item["link"]:
                            self.rss_feeds.append(item)
                    if self.rss_feeds:
                        break
            except Exception:
                continue

    async def crawl(self, progress_callback=None) -> list[CrawledPage]:
        """Execute the crawl. Returns list of CrawledPage objects."""
        async with httpx.AsyncClient(
            headers={"User-Agent": self.USER_AGENT},
            verify=True,
        ) as client:
            # Fetch robots.txt first
            self.robots_txt = await self.robots_checker.fetch_robots(client, self.base_url)

            if progress_callback:
                await progress_callback(0.05, "Checking robots.txt and sitemap...")

            # Parse sitemap
            await self._parse_sitemap(client)

            # Build seed URLs
            seeds = self._build_seed_urls()

            # Add high-priority sitemap URLs
            for entry in self.sitemap_entries[:20]:
                if entry["url"] not in seeds:
                    seeds.append(entry["url"])

            if progress_callback:
                await progress_callback(0.1, "Starting crawl...")

            # BFS crawl
            queue: list[tuple[str, int]] = [(url, 0) for url in seeds]
            crawled_count = 0

            while queue and len(self.pages) < self.max_pages:
                url, depth = queue.pop(0)
                if depth > MAX_DEPTH:
                    continue
                if url in self.visited:
                    continue

                page = await self._fetch_page(client, url)
                if page and page.status_code == 200 and page.html:
                    page.depth = depth
                    self.pages.append(page)
                    crawled_count += 1

                    if progress_callback:
                        pct = 0.1 + (0.4 * min(crawled_count / self.max_pages, 1.0))
                        await progress_callback(pct, f"Crawled {crawled_count} pages...")

                    # Add links to queue, prioritizing news-like URLs
                    new_links = []
                    for link in page.links:
                        if link not in self.visited:
                            priority = 0 if self._should_prioritize(link) else 1
                            new_links.append((priority, link, depth + 1))

                    new_links.sort(key=lambda x: x[0])
                    for _, link, d in new_links:
                        queue.append((link, d))

            if progress_callback:
                await progress_callback(0.5, "Parsing RSS feeds...")

            # Parse RSS feeds
            await self._parse_rss_feeds(client)

            if progress_callback:
                await progress_callback(0.55, "Crawl complete.")

        return self.pages
