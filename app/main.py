"""FastAPI application — serves job data from Redis."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db_client import db_client
from app.models import Job, JobSearchParams
from app.orchestrator import run_all
from app.redis_client import redis_client
from app.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    # Startup
    await db_client.connect()
    asyncio.create_task(db_client.init_db())
    await redis_client.connect()
    
    # Warm up Redis cache using latest Supabase jobs
    await redis_client.warm_up_cache()
    
    start_scheduler()
    logger.info("Background scheduler started")
    yield
    # Shutdown
    stop_scheduler()
    await redis_client.disconnect()
    await db_client.disconnect()
    logger.info("Shutdown complete")


# ── App ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Job Scraper API",
    description="Fast job aggregator API serving US-based listings from multiple ATS platforms via Redis.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpoints ────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Check API and Redis health."""
    redis_ok = await redis_client.health_check()
    return {
        "status": "ok" if redis_ok else "degraded",
        "redis": "connected" if redis_ok else "disconnected",
    }


@app.get("/jobs", response_model=list[Job])
async def list_jobs(
    keyword: str | None = Query(default=None, description="Search in title/description"),
    location: str | None = Query(default=None, description="Filter by location"),
    company: str | None = Query(default=None, description="Filter by company name"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=25, ge=1, le=100, description="Results per page"),
):
    """List/search jobs with optional filters. Served directly from Redis."""
    if keyword or location or company:
        jobs = await redis_client.search_jobs(
            keyword=keyword,
            location=location,
            company=company,
            page=page,
            limit=limit,
        )
    else:
        jobs = await redis_client.get_all_jobs(page=page, limit=limit)
    return jobs


@app.get("/jobs/recent", response_model=list[Job])
async def list_recent_jobs(
    days: float = Query(default=1.0, gt=0, le=60, description="Look-back window in days. Standard values: 1 (24h), 3, 7, 14."),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=25, ge=1, le=100, description="Results per page"),
):
    """Feed of jobs posted within the last `days`, newest-first.

    Recency uses the ATS-reported posted date (the source of truth): timestamp
    precision where the ATS provides it (greenhouse, lever), date precision for
    Workday. Mirrors the standard "Date posted: last 24h / 3 / 7 / 14 days" filter.
    """
    return await db_client.fetch_recent_jobs(days=days, page=page, limit=limit)


@app.get("/jobs/company/{company_slug}", response_model=list[Job])
async def get_jobs_by_company(
    company_slug: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
):
    """Get all jobs for a specific company (by slug). Served from Redis."""
    jobs = await redis_client.get_jobs_by_company(
        company_slug=company_slug.lower(),
        page=page,
        limit=limit,
    )
    return jobs


@app.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str):
    """Get a single job by its ID."""
    job = await redis_client.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/stats")
async def get_stats():
    """Get aggregate statistics (total, company-wise, portal-wise)."""
    return await redis_client.get_detailed_stats()


@app.post("/scrape")
async def trigger_scrape():
    """Manually trigger a full scrape run (async, returns when done)."""
    result = await run_all()
    return result
