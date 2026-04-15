"""
Base Scraper
============
Abstract base class for all PropIQ data scrapers.

Provides:
  - httpx AsyncClient with realistic browser headers
  - Retry logic (exponential backoff, 429 rate-limit handling)
  - Random inter-request delay (1–3 s) to avoid triggering bot-detection
  - Optional Playwright integration for JavaScript-heavy portals
  - BeautifulSoup parse helper
  - Structured logging with scraper name and timestamp
"""
from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.config import settings

logger = logging.getLogger(__name__)

# Rotate through common browser User-Agents so requests look organic
_USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
        "Gecko/20100101 Firefox/125.0"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
]

_BASE_HEADERS = {
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
}


class BaseScraper(ABC):
    """
    Async-first base scraper.  Use as an async context manager:

        async with MyScraper() as s:
            data = await s.fetch_page(url)
    """

    BASE_URL: str = ""
    SOURCE_NAME: str = "base"

    def __init__(self, use_proxy: bool = False) -> None:
        self._client: httpx.AsyncClient | None = None
        self._use_proxy = use_proxy
        self.delay_min = 1.0
        self.delay_max = 3.0
        self.max_retries: int = settings.SCRAPER_MAX_RETRIES
        self.timeout: int = settings.SCRAPER_TIMEOUT_SECONDS

    # ── Async context manager ─────────────────────────────────────────────────

    async def __aenter__(self) -> "BaseScraper":
        proxy = settings.SCRAPER_PROXY_URL if (self._use_proxy and hasattr(settings, "SCRAPER_PROXY_URL")) else None
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=True,
            headers={**_BASE_HEADERS, "User-Agent": random.choice(_USER_AGENTS)},
            proxy=proxy,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    # ── HTTP helpers ──────────────────────────────────────────────────────────

    async def fetch_page(
        self,
        url: str,
        method: str = "GET",
        data: dict | None = None,
        headers: dict | None = None,
    ) -> str:
        """
        Fetch a URL and return the response body as text.

        Implements:
        - Random 1–3 s delay before each request
        - 3 retries with exponential backoff
        - 429 rate-limit detection (backs off 2^attempt × 5 s)
        - Rotates User-Agent on each retry
        """
        assert self._client is not None, "Use BaseScraper as an async context manager"

        for attempt in range(1, self.max_retries + 1):
            # Randomised inter-request delay
            await asyncio.sleep(random.uniform(self.delay_min, self.delay_max))

            # Rotate UA on retries to reduce fingerprinting
            merged_headers = {
                "User-Agent": random.choice(_USER_AGENTS),
                **(headers or {}),
            }

            try:
                if method.upper() == "POST":
                    response = await self._client.post(
                        url, data=data, headers=merged_headers
                    )
                else:
                    response = await self._client.get(url, headers=merged_headers)

                if response.status_code == 429:
                    wait = (2 ** attempt) * 5
                    self.log(
                        f"Rate limited on {url}. Waiting {wait}s "
                        f"(attempt {attempt}/{self.max_retries})",
                        level="warning",
                    )
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()
                self.log(f"GET {url} → {response.status_code}")
                return response.text

            except httpx.HTTPStatusError as exc:
                self.log(
                    f"HTTP {exc.response.status_code} on {url} "
                    f"(attempt {attempt}/{self.max_retries})",
                    level="warning",
                )
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)

            except httpx.RequestError as exc:
                self.log(
                    f"Request error on {url}: {exc} "
                    f"(attempt {attempt}/{self.max_retries})",
                    level="warning",
                )
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(f"Failed to fetch {url} after {self.max_retries} attempts")

    async def fetch_with_js(self, url: str) -> str:
        """
        Render a JavaScript-heavy page using Playwright.
        Waits for networkidle before returning the page HTML.

        Requires ``playwright`` to be installed and browsers downloaded:
            pip install playwright && playwright install chromium
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "playwright is not installed. Run: pip install playwright && playwright install chromium"
            ) from exc

        await asyncio.sleep(random.uniform(self.delay_min, self.delay_max))

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=random.choice(_USER_AGENTS),
                locale="en-IN",
                extra_http_headers={
                    "Accept-Language": "en-IN,en;q=0.9",
                },
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)
            html = await page.content()
            await browser.close()
            self.log(f"JS-render {url} → {len(html)} bytes")
            return html

    # ── Parse helpers ─────────────────────────────────────────────────────────

    def parse_html(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def extract_text(self, element: Any) -> str:
        """Safely extract stripped text from a BeautifulSoup element."""
        if element is None:
            return ""
        return element.get_text(separator=" ", strip=True)

    # ── Logging ───────────────────────────────────────────────────────────────

    def log(self, message: str, level: str = "info") -> None:
        full = f"[{self.SOURCE_NAME}] {message}"
        getattr(logger, level.lower(), logger.info)(full)

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    async def scrape(self, *args: Any, **kwargs: Any) -> list[dict]:
        """Run the scraper. Returns a list of raw data dicts."""
        ...

    @abstractmethod
    async def save(self, records: list[dict], db: Any) -> int:
        """Persist scraped records. Returns count saved."""
        ...
