import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.db_client import db_client


async def main():
    print("Connecting to Supabase Database...")
    try:
        await db_client.connect()
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # 1. Total jobs count
    stats = await db_client.get_stats()
    print(f"\n[SUCCESS] Total jobs persisted in database: {stats['total_jobs']}")

    # 2. Company-wise breakdown
    print("\n[COMPANIES] Top Companies with jobs:")
    for company, count in list(stats["company_wise"].items())[:5]:
        print(f"  - {company}: {count} jobs")

    # 3. Portal-wise breakdown
    print("\n[PORTALS] ATS Portals breakdown:")
    for portal, count in stats["portal_wise"].items():
        print(f"  - {portal}: {count} jobs")

    # 4. Fetch latest 5 jobs
    print("\n[LATEST JOBS] Latest 5 jobs in database:")
    jobs = await db_client.fetch_all_jobs(page=1, limit=5)
    for i, job in enumerate(jobs, 1):
        print(f"\n[{i}] {job.title}")
        print(f"    Company: {job.company} ({job.source_ats})")
        print(f"    Location: {job.location}")
        print(f"    Apply URL: {job.apply_url}")
        print(f"    Scraped At: {job.scraped_at}")

    await db_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
