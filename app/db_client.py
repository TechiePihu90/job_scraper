"""Asynchronous PostgreSQL client for Supabase database operations."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, Any
import asyncpg

from app.config import settings
from app.models import Job
from app.utils.content_hash import generate_content_hash

logger = logging.getLogger(__name__)


def parse_iso(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601 date string to naive or timezone-aware datetime."""
    if not dt_str:
        return None
    try:
        # standard ISO format parsing
        if dt_str.endswith("Z"):
            dt_str = dt_str[:-1] + "+00:00"
        return datetime.fromisoformat(dt_str)
    except Exception:
        try:
            # Fallback for common sub-second formats
            return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f")
        except Exception:
            return None


class DBClient:
    """Async client managing the Supabase database connection pool and execution."""

    def __init__(self) -> None:
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Initialize the connection pool."""
        if self.pool is not None:
            return

        logger.info("Initializing Supabase database connection pool...")
        try:
            # Connect explicitly via individual parameters to prevent password URI parsing errors
            self.pool = await asyncpg.create_pool(
                host=settings.supabase_db_host,
                port=settings.supabase_db_port,
                user=settings.supabase_db_user,
                password=settings.supabase_db_password,
                database=settings.supabase_db_name,
                min_size=1,
                max_size=3,
                timeout=30.0,
            )
            logger.info("Supabase connection pool initialized successfully")
        except Exception as e:
            logger.error("Failed to connect to Supabase database: %s", e, exc_info=True)
            raise

    async def disconnect(self) -> None:
        """Shutdown the connection pool."""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
            logger.info("Supabase database connection pool closed")

    async def init_db(self) -> None:
        """Ensure the jobs table and associated indexes exist in Supabase."""
        sql = """
        -- Create jobs table
        CREATE TABLE IF NOT EXISTS jobs (
            job_id VARCHAR(255) PRIMARY KEY,
            title VARCHAR(500) NOT NULL,
            company VARCHAR(255) NOT NULL,
            company_slug VARCHAR(255) NOT NULL,
            location VARCHAR(255) NOT NULL,
            description TEXT DEFAULT '',
            content_hash VARCHAR(64) NOT NULL,
            posted_at TIMESTAMP WITH TIME ZONE,
            apply_url TEXT NOT NULL,
            source_ats VARCHAR(100) NOT NULL,
            scraped_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'utc') NOT NULL
        );

        -- Index for fetching jobs by company slug (routes filter)
        CREATE INDEX IF NOT EXISTS idx_jobs_company_slug ON jobs(company_slug);

        -- Index for global job feed pagination (sorted newest first)
        CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at_desc ON jobs(scraped_at DESC);

        -- Index for filtering by company
        CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);

        -- Index for full-text search across titles and descriptions
        CREATE INDEX IF NOT EXISTS idx_jobs_fts ON jobs USING gin(
            to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))
        );

        -- Ensure content_hash column exists for deduplication on upgrades
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);

        -- Unique index on content_hash to prevent duplicate postings
        CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_content_hash_unique ON jobs(content_hash);
        """
        if self.pool is None:
            raise RuntimeError("Database client not connected")

        async with self.pool.acquire() as conn:
            await conn.execute(sql)
            logger.info("Supabase database schema verified successfully")

    async def upsert_jobs(self, jobs: list[Job]) -> int:
        """Bulk upsert jobs into the Supabase database. Returns count of successfully upserted jobs."""
        if not jobs:
            return 0

        sql = """
        INSERT INTO jobs (
            job_id, title, company, company_slug, location, description, posted_at, apply_url, source_ats, scraped_at, content_hash
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (job_id) DO UPDATE SET
            title = EXCLUDED.title,
            company = EXCLUDED.company,
            company_slug = EXCLUDED.company_slug,
            location = EXCLUDED.location,
            description = EXCLUDED.description,
            posted_at = EXCLUDED.posted_at,
            apply_url = EXCLUDED.apply_url,
            source_ats = EXCLUDED.source_ats,
            scraped_at = EXCLUDED.scraped_at,
            content_hash = EXCLUDED.content_hash;
        """
        if self.pool is None:
            await self.connect()

        assert self.pool is not None
        success_count = 0
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for job in jobs:
                    scraped_dt = parse_iso(job.scraped_at) or datetime.utcnow()
                    posted_dt = parse_iso(job.posted_at)
                    try:
                        # Ensure content_hash exists for the job (compute if missing)
                        if not getattr(job, "content_hash", None):
                            job.content_hash = generate_content_hash(
                                job.title, job.company_slug(), job.location, job.description
                            )
                        await conn.execute(
                            sql,
                            job.job_id,
                            job.title,
                            job.company,
                            job.company_slug(),
                            job.location,
                            job.description,
                            posted_dt,
                            job.apply_url,
                            job.source_ats,
                            scraped_dt,
                            getattr(job, "content_hash", None),
                        )
                        success_count += 1
                    except Exception as e:
                        logger.error("Failed to upsert job %s into Supabase: %s", job.job_id, e)

        logger.info("Successfully persisted %d/%d jobs in Supabase", success_count, len(jobs))
        return success_count

    async def content_hash_exists(self, content_hash: str) -> bool:
        """Check whether a content_hash already exists in the jobs table."""
        if not content_hash:
            return False

        if self.pool is None:
            await self.connect()

        assert self.pool is not None
        sql = "SELECT 1 FROM jobs WHERE content_hash = $1 LIMIT 1"
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(sql, content_hash)
            return val is not None

    async def fetch_job(self, job_id: str) -> Optional[Job]:
        """Fetch a single job by its ID."""
        if self.pool is None:
            await self.connect()

        assert self.pool is not None
        sql = "SELECT * FROM jobs WHERE job_id = $1"
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(sql, job_id)
            if not row:
                return None
            return self._row_to_job(row)

    async def fetch_all_jobs(self, page: int = 1, limit: int = 25) -> list[Job]:
        """Get all jobs paginated, ordered by scraped_at DESC."""
        if self.pool is None:
            await self.connect()

        assert self.pool is not None
        offset = (page - 1) * limit
        sql = "SELECT * FROM jobs ORDER BY scraped_at DESC LIMIT $1 OFFSET $2"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, limit, offset)
            return [self._row_to_job(r) for r in rows]

    async def fetch_jobs_by_company(self, company_slug: str, page: int = 1, limit: int = 25) -> list[Job]:
        """Get jobs for a specific company by slug."""
        if self.pool is None:
            await self.connect()

        assert self.pool is not None
        offset = (page - 1) * limit
        sql = "SELECT * FROM jobs WHERE company_slug = $1 ORDER BY scraped_at DESC LIMIT $2 OFFSET $3"
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, company_slug, limit, offset)
            return [self._row_to_job(r) for r in rows]

    async def search_jobs(
        self,
        keyword: Optional[str] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        page: int = 1,
        limit: int = 25,
    ) -> list[Job]:
        """Search jobs using filters and PostgreSQL Full-Text search."""
        if self.pool is None:
            await self.connect()

        assert self.pool is not None
        offset = (page - 1) * limit
        conditions = []
        params = []
        param_idx = 1

        if keyword:
            conditions.append(
                f"to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '')) @@ plainto_tsquery('english', ${param_idx})"
            )
            params.append(keyword)
            param_idx += 1

        if location:
            conditions.append(f"location ILIKE ${param_idx}")
            params.append(f"%{location}%")
            param_idx += 1

        if company:
            conditions.append(f"company ILIKE ${param_idx}")
            params.append(f"%{company}%")
            param_idx += 1

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        sql = f"SELECT * FROM jobs{where_clause} ORDER BY scraped_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        params.extend([limit, offset])

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [self._row_to_job(r) for r in rows]

    async def get_stats(self) -> dict:
        """Compute aggregate statistics from the database."""
        if self.pool is None:
            await self.connect()

        assert self.pool is not None
        total_sql = "SELECT COUNT(*) FROM jobs"
        company_sql = "SELECT company, COUNT(*) as count FROM jobs GROUP BY company ORDER BY count DESC"
        portal_sql = "SELECT source_ats, COUNT(*) as count FROM jobs GROUP BY source_ats ORDER BY count DESC"

        async with self.pool.acquire() as conn:
            total_count = await conn.fetchval(total_sql)
            company_rows = await conn.fetch(company_sql)
            portal_rows = await conn.fetch(portal_sql)

            return {
                "total_jobs": total_count,
                "company_wise": {r["company"]: r["count"] for r in company_rows},
                "portal_wise": {r["source_ats"]: r["count"] for r in portal_rows},
            }

    def _row_to_job(self, row: asyncpg.Record) -> Job:
        """Convert a database record row to a validated Job object."""
        posted_at_val = row["posted_at"].isoformat() if row["posted_at"] else None
        scraped_at_val = row["scraped_at"].isoformat() if row["scraped_at"] else datetime.utcnow().isoformat()

        return Job(
            job_id=row["job_id"],
            title=row["title"],
            company=row["company"],
            location=row["location"],
            description=row["description"] or "",
            posted_at=posted_at_val,
            apply_url=row["apply_url"],
            source_ats=row["source_ats"],
            scraped_at=scraped_at_val,
            content_hash=row.get("content_hash"),
        )


# Singleton database client instance
db_client = DBClient()
