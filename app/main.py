"""FastAPI application — serves job data from the Supabase-backed database."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db_client import db_client
from app.models import Job

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    await db_client.connect()
    asyncio.create_task(db_client.init_db())
    yield
    await db_client.disconnect()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Job Scraper API",
    description="Fast job aggregator API serving US-based listings from multiple ATS platforms from the database.",
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


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """Check API and database health."""
    try:
        await db_client.connect()
        return {
            "status": "ok",
            "database": "connected",
        }
    except Exception as exc:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail=503) from exc


@app.get("/")
async def root():
    return {
        "message": "Welcome to Job Scraper API 🚀",
        "docs": "/docs",
        "jobs": "/jobs",
        "stats": "/stats",
    }


@app.get("/jobs", response_model=list[Job])
async def list_jobs(
    keyword: str | None = Query(default=None, description="Search in title/description"),
    location: str | None = Query(default=None, description="Filter by location"),
    company: str | None = Query(default=None, description="Filter by company name"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=25, ge=1, le=100, description="Results per page"),
):
    """List/search jobs with optional filters from the database."""
    if keyword or location or company:
        jobs = await db_client.search_jobs(
            keyword=keyword,
            location=location,
            company=company,
            page=page,
            limit=limit,
        )
    else:
        jobs = await db_client.fetch_all_jobs(page=page, limit=limit)
    return jobs


@app.get("/jobs/company/{company_slug}", response_model=list[Job])
async def get_jobs_by_company(
    company_slug: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
):
    """Get all jobs for a specific company (by slug) from the database."""
    jobs = await db_client.fetch_jobs_by_company(
        company_slug=company_slug.lower(),
        page=page,
        limit=limit,
    )
    return jobs


@app.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: str):
    """Get a single job by its ID."""
    job = await db_client.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/stats")
async def get_stats():
    """Get aggregate statistics (total, company-wise, portal-wise)."""
    return await db_client.get_stats()