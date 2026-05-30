
import asyncio
import json
from app.redis_client import redis_client

async def fetch_jobs():
    await redis_client.connect()
    jobs = await redis_client.get_all_jobs(limit=10)
    print(f"Total jobs found in Redis: {len(jobs)}")
    for job in jobs:
        print(f"Title: {job.title}")
        print(f"URL: {job.apply_url}")
        print(f"Company: {job.company}")
        print(f"Description (excerpt): {job.description[:100]}...")
        print("-" * 20)
    await redis_client.disconnect()

if __name__ == "__main__":
    asyncio.run(fetch_jobs())
