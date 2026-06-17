"""Abstract base scraper with shared utilities for all ATS platforms."""

from __future__ import annotations

import hashlib
import html
import logging
import re
from abc import ABC, abstractmethod
from urllib.parse import urlparse

import aiohttp
from bs4 import BeautifulSoup

from app.config import settings
from app.models import CompanyConfig, Job
from app.redis_client import RedisClient
from app.utils.location import is_us_location
from app.utils.it_titles import is_it_job
from app.utils.rate_limiter import AsyncRateLimiter
from app.utils.retry import retry_with_backoff
from app.utils.content_hash import generate_content_hash

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for ATS scrapers.

    Subclasses must implement `scrape()` which returns a list of normalized Job objects.
    The base class provides shared HTTP helpers, rate limiting, retry logic,
    and US-location filtering.
    """

    ATS_NAME: str = "unknown"

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(
        self,
        company: CompanyConfig,
        session: aiohttp.ClientSession,
        redis: RedisClient,
        rate_limiter: AsyncRateLimiter,
    ) -> None:
        self.company = company
        self.session = session
        self.redis = redis
        self.rate_limiter = rate_limiter
        self.logger = logging.getLogger(f"scraper.{self.ATS_NAME}.{company.name}")

    # ── Abstract ─────────────────────────────────────────────────────────

    @abstractmethod
    async def scrape(self) -> list[Job]:
        """Scrape all US-based jobs for this company. Must be implemented by subclass."""
        ...

    # ── HTTP Helpers ─────────────────────────────────────────────────────

    @retry_with_backoff(
        max_retries=settings.max_retries,
        base_delay=settings.retry_base_delay,
        exceptions=(aiohttp.ClientError, TimeoutError),
    )
    async def _get(self, url: str, **kwargs) -> dict | list | str:
        """Rate-limited GET request with retry + backoff. Returns parsed JSON or text."""
        domain = urlparse(url).hostname or "unknown"
        headers = {**self.DEFAULT_HEADERS, **kwargs.pop("headers", {})}
        async with self.rate_limiter(domain):
            self.logger.debug("GET %s", url)
            async with self.session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=settings.request_timeout_seconds),
                **kwargs,
            ) as resp:
                resp.raise_for_status()
                content_type = resp.content_type or ""
                if "json" in content_type:
                    return await resp.json()
                return await resp.text()

    @retry_with_backoff(
        max_retries=settings.max_retries,
        base_delay=settings.retry_base_delay,
        exceptions=(aiohttp.ClientError, TimeoutError),
    )
    async def _post(self, url: str, json_data: dict | None = None, **kwargs) -> dict | list:
        """Rate-limited POST request with retry + backoff."""
        domain = urlparse(url).hostname or "unknown"
        headers = {**self.DEFAULT_HEADERS, **kwargs.pop("headers", {})}
        async with self.rate_limiter(domain):
            self.logger.debug("POST %s", url)
            async with self.session.post(
                url,
                json=json_data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=settings.request_timeout_seconds),
                **kwargs,
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    # ── Filtering ────────────────────────────────────────────────────────

    def filter_us_jobs(self, jobs: list[Job]) -> list[Job]:
        """Filter a list of jobs to only include US-based locations."""
        us_jobs = [j for j in jobs if is_us_location(j.location)]
        self.logger.info(
            "US-filter: %d/%d jobs passed for %s",
            len(us_jobs),
            len(jobs),
            self.company.name,
        )
        return us_jobs

    def filter_it_jobs(self, jobs: list[Job]) -> list[Job]:
        """Filter a list of jobs to only include IT-related titles."""
        it_jobs = [j for j in jobs if is_it_job(j.title)]
        self.logger.info(
            "IT-filter: %d/%d jobs passed for %s",
            len(it_jobs),
            len(jobs),
            self.company.name,
        )
        return it_jobs

    # ── Utilities ────────────────────────────────────────────────────────

    @staticmethod
    def generate_job_id(ats: str, company: str, external_id: str) -> str:
        """Generate a deterministic, globally unique job ID.
        Uses the ATS name and the original external ID to keep it human-readable.
        """
        # We lowercase and strip special chars to keep it clean
        clean_ats = ats.lower().replace(" ", "")
        return f"{clean_ats}-{external_id}"

    @staticmethod
    def normalize_text(text: str | None) -> str:
        """Normalize scraped text for clean API output.

        - Decode HTML entities like &nbsp;
        - Replace non-breaking spaces with normal spaces
        - Convert HTML to readable text without losing nested content
        - Collapse repeated whitespace into a single readable form
        """
        if not text:
            return ""

        text = html.unescape(text)
        text = text.replace("\xa0", " ")

        # Use BeautifulSoup for real HTML parsing so nested content is preserved.
        if "<" in text and ">" in text:
            try:
                text = BeautifulSoup(text, "html.parser").get_text("\n", strip=False)
            except Exception:
                text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
                text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
                text = re.sub(r"<[^>]+>", " ", text)

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\u00a0", " ", text)
        text = re.sub(r"[ \t\f\v]+", " ", text)
        text = re.sub(r"\n[ \t\f\v]*\n+", "\n\n", text)
        text = re.sub(r"[ \t]+\n", "\n", text)
        return text.strip()

    async def run(self) -> int:
        """Execute the full scrape pipeline: scrape → filter → store.

        Returns count of newly stored jobs.
        Raises the exception if the scrape fails.
        """
        self.logger.info("Starting scrape for %s (%s)", self.company.name, self.ATS_NAME)
        jobs = await self.scrape()
        
        if not jobs:
            self.logger.warning("No jobs found for %s", self.company.name)
            return 0
            
        self.logger.info("✓ Scraped %d jobs for %s", len(jobs), self.company.name)
        
        us_jobs = self.filter_us_jobs(jobs)
        
        if not us_jobs:
            self.logger.warning("⚠ All jobs filtered out! %d scraped → 0 US jobs for %s", len(jobs), self.company.name)
            return 0
        
        if settings.scrape_it_only:
            it_jobs = self.filter_it_jobs(us_jobs)
            final_jobs = it_jobs
            if not it_jobs:
                self.logger.warning("⚠ All US jobs filtered out! %d US → 0 IT jobs for %s", len(us_jobs), self.company.name)
                return 0
        else:
            final_jobs = us_jobs
        
        # Persist permanently in Supabase database (best-effort)
        from app.db_client import db_client

        # Compute content hashes and skip duplicates that already exist in DB
        to_persist: list[Job] = []
        for job in final_jobs:
            ch = generate_content_hash(job.title, job.company_slug(), job.location, job.description)
            job.content_hash = ch
            try:
                exists = await db_client.content_hash_exists(ch)
            except Exception:
                # If the DB check fails, be conservative and include the job for upsert
                exists = False

            if exists:
                self.logger.debug("Skipping duplicate job by content_hash for %s: %s", self.company.name, job.job_id)
            else:
                to_persist.append(job)

        try:
            db_stored = await db_client.upsert_jobs(to_persist)
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("DB upsert failed for %s: %s", self.company.name, exc, exc_info=True)
            db_stored = 0

        # Cache in Redis (always attempt, even if DB upsert failed)
        try:
            redis_stored = await self.redis.store_jobs(final_jobs)
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.error("Redis caching failed for %s: %s", self.company.name, exc, exc_info=True)
            redis_stored = 0
        
        self.logger.info(
            "✓ Completed %s: %d scraped → %d US → %d final → %d persisted → %d cached",
            self.company.name,
            len(jobs),
            len(us_jobs),
            len(final_jobs),
            db_stored,
            redis_stored,
        )
        return db_stored
