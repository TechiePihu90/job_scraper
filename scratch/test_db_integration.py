import asyncio
import sys
from pathlib import Path

# Add project root to Python search path
sys.path.append(str(Path(__file__).parent.parent))

from app.db_client import db_client
from app.redis_client import redis_client
from app.models import Job


async def main():
    print("Testing Supabase Database and Redis connection...")

    # 1. Test database connection
    try:
        await db_client.connect()
        print("[SUCCESS] Connected to Supabase DB and verified schema.")
    except Exception as e:
        print(f"[FAILED] Database connection failed: {e}")
        return

    # 2. Test Redis connection
    try:
        await redis_client.connect()
        print("[SUCCESS] Connected to Redis Cache.")
    except Exception as e:
        print(f"[FAILED] Redis connection failed: {e}")

    # 3. Test db upsert and retrieve
    test_job = Job(
        job_id="test-ats-12345",
        title="Test Software Engineer",
        company="TechiePihu Inc",
        location="San Francisco, CA",
        description="This is a test description of the job.",
        posted_at="2026-05-19T12:00:00Z",
        apply_url="https://example.com/apply/12345",
        source_ats="Greenhouse",
        scraped_at="2026-05-19T17:00:00Z",
    )

    print("\nAttempting to upsert test job in database...")
    try:
        inserted = await db_client.upsert_jobs([test_job])
        print(f"[SUCCESS] Upserted {inserted} job(s) in Supabase.")
    except Exception as e:
        print(f"[FAILED] Failed to upsert job: {e}")

    print("\nFetching the upserted job by ID...")
    try:
        job = await db_client.fetch_job("test-ats-12345")
        if job:
            print(f"[SUCCESS] Found job: {job.title} at {job.company}")
            print(f"          Apply URL: {job.apply_url}")
            print(f"          Scraped at: {job.scraped_at}")
        else:
            print("[FAILED] Job not found in database.")
    except Exception as e:
        print(f"[FAILED] Failed to fetch job: {e}")

    # 4. Test stats
    print("\nFetching aggregate stats from database...")
    try:
        stats = await db_client.get_stats()
        print(f"[SUCCESS] Current Stats: {stats}")
    except Exception as e:
        print(f"[FAILED] Failed to fetch stats: {e}")

    # 5. Test Redis cache-aside fallback
    print("\nTesting Redis cache-aside fallback...")
    try:
        # Clear the specific key in Redis to force cache miss
        await redis_client.pool.delete("job:test-ats-12345")
        print(
            "Cleared 'job:test-ats-12345' from Redis. Querying redis_client.get_job (should trigger cache miss & fetch from Supabase)..."
        )

        cached_job = await redis_client.get_job("test-ats-12345")
        if cached_job:
            print(f"[SUCCESS] Cache-aside resolved: Found job {cached_job.title}")
            # Verify it's cached in Redis now
            in_redis = await redis_client.pool.exists("job:test-ats-12345")
            print(f"          Is now cached in Redis: {bool(in_redis)}")
        else:
            print("[FAILED] Cache-aside did not find the job.")
    except Exception as e:
        print(f"[FAILED] Cache-aside test failed: {e}")

    # Cleanup connections
    await db_client.disconnect()
    await redis_client.disconnect()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
