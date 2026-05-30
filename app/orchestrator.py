"""Scraper orchestrator — runs all scrapers concurrently with bounded parallelism."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

import aiohttp

from app.config import settings
from app.models import CompanyConfig
from app.redis_client import redis_client
from app.scrapers import SCRAPER_REGISTRY
from app.utils.rate_limiter import AsyncRateLimiter

logger = logging.getLogger(__name__)


async def load_companies(path: str | None = None) -> list[CompanyConfig]:
    """Load company configs from the JSON file."""
    config_path = Path(path or settings.companies_config_path)
    if not config_path.exists():
        logger.error("Companies config not found: %s", config_path)
        return []

    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    companies = [CompanyConfig(**entry) for entry in data.get("companies", [])]
    logger.info("Loaded %d companies from %s", len(companies), config_path)
    return companies


async def scrape_company(
    company: CompanyConfig,
    session: aiohttp.ClientSession,
    rate_limiter: AsyncRateLimiter,
    semaphore: asyncio.Semaphore,
) -> int:
    """Scrape a single company (guarded by semaphore)."""
    async with semaphore:
        scraper_cls = SCRAPER_REGISTRY.get(company.ats_type)
        if scraper_cls is None:
            logger.warning("No scraper registered for ATS type: %s", company.ats_type)
            return 0

        scraper = scraper_cls(
            company=company,
            session=session,
            redis=redis_client,
            rate_limiter=rate_limiter,
        )
        return await scraper.run()


async def run_all(config_path: str | None = None) -> dict:
    """Run all scrapers concurrently. Returns a summary dict."""
    start = time.monotonic()
    companies = await load_companies(config_path)
    if not companies:
        return {"status": "no_companies", "total_new_jobs": 0}

    await redis_client.connect()
    semaphore = asyncio.Semaphore(settings.max_concurrent_scrapers)
    rate_limiter = AsyncRateLimiter(rate=settings.rate_limit_per_second)

    connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
    async with aiohttp.ClientSession(
        connector=connector,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
    ) as session:
        tasks = [
            scrape_company(company, session, rate_limiter, semaphore)
            for company in companies
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    total_new = 0
    errors = 0
    error_details = []
    
    for i, result in enumerate(results):
        company_name = companies[i].name
        if isinstance(result, Exception):
            logger.error("Company %s failed with exception: %s", company_name, result)
            errors += 1
            error_details.append({"company": company_name, "error": str(result)})
        elif result == 0:
            # If it returned 0, it might be a silent failure or just no jobs.
            # We already logged this in BaseScraper.run()
            pass
        else:
            total_new += result

    elapsed = time.monotonic() - start
    summary = {
        "status": "completed",
        "companies_total": len(companies),
        "companies_with_jobs": sum(1 for r in results if isinstance(r, int) and r > 0),
        "errors_count": errors,
        "total_new_jobs": total_new,
        "duration_seconds": round(elapsed, 2),
    }
    if error_details:
        summary["error_samples"] = error_details[:5]
        
    logger.info("Scrape run complete: %s", summary)
    return summary


# CLI entry point
if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    result = asyncio.run(run_all())
    print(json.dumps(result, indent=2))
