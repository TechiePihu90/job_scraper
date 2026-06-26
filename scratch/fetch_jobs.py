import asyncio

from app.db_client import db_client


async def fetch_jobs():
    await db_client.connect()
    jobs = await db_client.fetch_all_jobs(page=1, limit=10)
    print(f"Total jobs found in database: {len(jobs)}")
    for job in jobs:
        print(f"Title: {job.title}")
        print(f"URL: {job.apply_url}")
        print(f"Company: {job.company}")
        print(f"Description (excerpt): {job.description[:100]}...")
        print("-" * 20)
    await db_client.disconnect()


if __name__ == "__main__":
    asyncio.run(fetch_jobs())
