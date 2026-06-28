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
    http_semaphore: asyncio.Semaphore,
    browser_semaphore: asyncio.Semaphore,
) -> int:
    """Scrape a single company, throttled by the semaphore for its scraper type."""
    scraper_cls = SCRAPER_REGISTRY.get(company.ats_type)
    if scraper_cls is None:
        logger.warning("No scraper registered for ATS type: %s", company.ats_type)
        return 0

    # Browser-based scrapers (Playwright) use a separate, much smaller pool so
    # they can't spawn dozens of Chromium processes at once and exhaust memory.
    semaphore = browser_semaphore if getattr(scraper_cls, "USES_BROWSER", False) else http_semaphore

    async with semaphore:
        scraper = scraper_cls(
            company=company,
            session=session,
            rate_limiter=rate_limiter,
        )
        return await scraper.run()


async def run_all(config_path: str | None = None) -> dict:
    """Run all scrapers concurrently. Returns a summary dict."""
    import datetime as _dt

    start = time.monotonic()
    started_at = _dt.datetime.utcnow().isoformat()
    companies = await load_companies(config_path)
    if not companies:
        return {"status": "no_companies", "total_new_jobs": 0}

    semaphore = asyncio.Semaphore(settings.max_concurrent_scrapers)
    browser_semaphore = asyncio.Semaphore(settings.max_concurrent_browsers)
    rate_limiter = AsyncRateLimiter(rate=settings.rate_limit_per_second)

    connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
    async with aiohttp.ClientSession(
        connector=connector,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
    ) as session:
        tasks = [
            scrape_company(company, session, rate_limiter, semaphore, browser_semaphore)
            for company in companies
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    total_new = 0
    errors = 0
    error_details = []
    ats_breakdown: dict[str, int] = {}

    for i, result in enumerate(results):
        company_name = companies[i].name
        ats = companies[i].ats_type
        if isinstance(result, Exception):
            logger.error("Company %s failed with exception: %s", company_name, result)
            errors += 1
            error_details.append({"company": company_name, "ats": ats, "error": str(result)})
        else:
            # result is an int: jobs newly stored for this company
            total_new += result
            ats_breakdown[ats] = ats_breakdown.get(ats, 0) + result

    elapsed = time.monotonic() - start
    summary = {
        "status": "completed",
        "started_at": started_at,
        "companies_total": len(companies),
        "companies_with_jobs": sum(1 for r in results if isinstance(r, int) and r > 0),
        "errors_count": errors,
        "total_new_jobs": total_new,
        "ats_breakdown": dict(sorted(ats_breakdown.items(), key=lambda x: x[1], reverse=True)),
        "duration_seconds": round(elapsed, 2),
    }
    if error_details:
        summary["error_samples"] = error_details[:5]

    logger.info("Scrape run complete: %s", summary)

    # Best-effort: persist a one-row audit log for this run.
    from app.db_client import db_client

    await db_client.record_run(summary)
    return summary


async def main() -> dict:
    """Standalone entry point: connect DB, ensure schema, run all scrapers, disconnect.

    Designed to be invoked as `python -m app.orchestrator` by a scheduled job
    (e.g. GitHub Actions) — not from inside the web process.
    """
    from app.db_client import db_client

    await db_client.connect()
    try:
        await db_client.init_db()
        result = await run_all()
    finally:
        await db_client.disconnect()
    return result


# CLI entry point
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    result = asyncio.run(main())
    print(json.dumps(result, indent=2))

    # Exit non-zero so the scheduler (GitHub Actions) reports a red run when the
    # scrape could not start. Per-company failures are reported in the summary.
    if result.get("status") != "completed":
        sys.exit(1)
