import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.db_client import db_client
from app.models import Job


async def main():
    print("Testing Supabase Database connection...")

    try:
        await db_client.connect()
        print("[SUCCESS] Connected to Supabase DB and verified schema.")
    except Exception as e:
        print(f"[FAILED] Database connection failed: {e}")
        return

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

    print("\nFetching aggregate stats from database...")
    try:
        stats = await db_client.get_stats()
        print(f"[SUCCESS] Current Stats: {stats}")
    except Exception as e:
        print(f"[FAILED] Failed to fetch stats: {e}")

    await db_client.disconnect()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
