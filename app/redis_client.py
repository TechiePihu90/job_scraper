"""Async Redis client for job storage and retrieval."""

from __future__ import annotations

import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings
from app.models import Job

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis wrapper for the job scraper storage layer.

    Key schema:
        job:{job_id}            → JSON string of the Job object
        company:{slug}:jobs     → SET of job_id strings
        jobs:all                → SORTED SET (score = timestamp) of job_id strings
    """

    def __init__(self, url: str | None = None) -> None:
        self._url = url or settings.redis_url
        self._pool: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Initialize the connection pool. Falls back to fakeredis if unavailable."""
        try:
            self._pool = aioredis.from_url(
                self._url,
                max_connections=settings.redis_max_connections,
                decode_responses=True,
            )
            await self._pool.ping()
            logger.info("Redis connected at %s", self._url)
        except Exception as exc:
            logger.warning("Real Redis unavailable (%s), falling back to fakeredis (in-memory)", exc)
            try:
                import fakeredis.aioredis as fakeasync
                self._pool = fakeasync.FakeRedis(decode_responses=True)
                await self._pool.ping()
                logger.info("fakeredis (in-memory) connected — data will NOT persist across restarts")
            except ImportError:
                raise RuntimeError(
                    "Cannot connect to Redis and fakeredis is not installed. "
                    "Install fakeredis (`pip install fakeredis`) or start Redis."
                ) from exc

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.aclose()
            logger.info("Redis connection closed")

    @property
    def pool(self) -> aioredis.Redis:
        if self._pool is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._pool

    # ── Storage ──────────────────────────────────────────────────────────

    async def store_job(self, job: Job) -> bool:
        """Store a job in Redis. Returns True if new, False if duplicate."""
        key = job.to_redis_key()

        if await self.pool.exists(key):
            logger.debug("Duplicate job skipped: %s", key)
            return False

        pipe = self.pool.pipeline()
        pipe.set(key, job.model_dump_json(), ex=settings.job_ttl_seconds)
        pipe.sadd(f"company:{job.company_slug()}:jobs", job.job_id)
        pipe.expire(f"company:{job.company_slug()}:jobs", settings.job_ttl_seconds)

        # Sorted set for global listing — score is scraped_at epoch
        import datetime as _dt

        try:
            ts = _dt.datetime.fromisoformat(job.scraped_at).timestamp()
        except Exception:
            ts = _dt.datetime.utcnow().timestamp()
        pipe.zadd("jobs:all", {job.job_id: ts})

        await pipe.execute()
        logger.debug("Stored job: %s (%s)", job.title, job.company)
        return True

    async def store_jobs(self, jobs: list[Job]) -> int:
        """Bulk-store a list of jobs. Returns count of newly stored jobs."""
        stored = 0
        for job in jobs:
            if await self.store_job(job):
                stored += 1
        return stored

    # ── Retrieval ────────────────────────────────────────────────────────

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a single job by ID with a cache-aside database fallback."""
        raw = await self.pool.get(f"job:{job_id}")
        if raw is not None:
            return Job.model_validate_json(raw)
        
        # Cache miss — fall back to Supabase database
        from app.db_client import db_client
        job = await db_client.fetch_job(job_id)
        if job is not None:
            await self.store_job(job)
        return job

    async def get_jobs_by_company(
        self, company_slug: str, page: int = 1, limit: int = 25
    ) -> list[Job]:
        """Get all jobs for a given company with database fallback."""
        job_ids = await self.pool.smembers(f"company:{company_slug}:jobs")
        if not job_ids:
            from app.db_client import db_client
            jobs = await db_client.fetch_jobs_by_company(company_slug, page=page, limit=limit)
            if jobs:
                await self.store_jobs(jobs)
            return jobs

        sorted_ids = sorted(job_ids)
        start = (page - 1) * limit
        end = start + limit
        page_ids = sorted_ids[start:end]

        jobs: list[Job] = []
        if page_ids:
            keys = [f"job:{jid}" for jid in page_ids]
            results = await self.pool.mget(*keys)
            for raw in results:
                if raw:
                    jobs.append(Job.model_validate_json(raw))
        return jobs

    async def search_jobs(
        self,
        keyword: str | None = None,
        location: str | None = None,
        company: str | None = None,
        page: int = 1,
        limit: int = 25,
    ) -> list[Job]:
        """Search/filter jobs across all stored listings with database fallback."""
        all_ids = await self.pool.zrevrange("jobs:all", 0, -1)
        if not all_ids:
            from app.db_client import db_client
            jobs = await db_client.search_jobs(
                keyword=keyword,
                location=location,
                company=company,
                page=page,
                limit=limit
            )
            if jobs:
                await self.store_jobs(jobs)
            return jobs

        # Batch-fetch all job JSONs
        keys = [f"job:{jid}" for jid in all_ids]
        raw_jobs = await self.pool.mget(*keys)

        filtered: list[Job] = []
        kw_lower = keyword.lower() if keyword else None
        loc_lower = location.lower() if location else None
        comp_lower = company.lower() if company else None

        for raw in raw_jobs:
            if raw is None:
                continue
            job = Job.model_validate_json(raw)

            if kw_lower and kw_lower not in job.title.lower() and kw_lower not in job.description.lower():
                continue
            if loc_lower and loc_lower not in job.location.lower():
                continue
            if comp_lower and comp_lower not in job.company.lower():
                continue

            filtered.append(job)

        start = (page - 1) * limit
        return filtered[start : start + limit]

    async def get_all_jobs(self, page: int = 1, limit: int = 25) -> list[Job]:
        """Get all jobs with pagination (newest first) and database fallback."""
        start = (page - 1) * limit
        end = start + limit - 1
        job_ids = await self.pool.zrevrange("jobs:all", start, end)
        if not job_ids:
            from app.db_client import db_client
            jobs = await db_client.fetch_all_jobs(page=page, limit=limit)
            if jobs:
                await self.store_jobs(jobs)
            return jobs

        keys = [f"job:{jid}" for jid in job_ids]
        results = await self.pool.mget(*keys)
        return [Job.model_validate_json(r) for r in results if r]

    async def get_total_jobs_count(self) -> int:
        """Get total number of jobs in the global sorted set."""
        return await self.pool.zcard("jobs:all")

    async def get_detailed_stats(self) -> dict:
        """Get aggregate statistics (total, company-wise, portal-wise)."""
        all_ids = await self.pool.zrange("jobs:all", 0, -1)
        
        company_stats = {}
        portal_stats = {}
        
        if all_ids:
            keys = [f"job:{jid}" for jid in all_ids]
            # Fetch in one go (Redis can handle thousands of keys in MGET)
            raw_jobs = await self.pool.mget(*keys)
            
            for raw in raw_jobs:
                if not raw:
                    continue
                job = Job.model_validate_json(raw)
                
                # Company-wise
                company_stats[job.company] = company_stats.get(job.company, 0) + 1
                
                # Portal-wise (ATS)
                portal_stats[job.source_ats] = portal_stats.get(job.source_ats, 0) + 1
                
        return {
            "total_jobs": len(all_ids),
            "company_wise": dict(sorted(company_stats.items(), key=lambda x: x[1], reverse=True)),
            "portal_wise": dict(sorted(portal_stats.items(), key=lambda x: x[1], reverse=True))
        }

    async def job_exists(self, job_id: str) -> bool:
        """Check if a job already exists (deduplication)."""
        return bool(await self.pool.exists(f"job:{job_id}"))

    async def warm_up_cache(self) -> int:
        """Warm up Redis cache using the latest 1000 jobs from Supabase."""
        from app.db_client import db_client
        logger.info("Warming up Redis cache from Supabase database...")
        try:
            jobs = await db_client.fetch_all_jobs(page=1, limit=1000)
            if not jobs:
                logger.info("No jobs found in Supabase to warm up cache")
                return 0
            
            stored = await self.store_jobs(jobs)
            logger.info("Successfully warmed up Redis cache with %d jobs from Supabase", stored)
            return stored
        except Exception as e:
            logger.error("Failed to warm up Redis cache: %s", e)
            return 0

    async def health_check(self) -> bool:
        """Check Redis connectivity."""
        try:
            return await self.pool.ping()
        except Exception:
            return False


# Singleton instance
redis_client = RedisClient()
