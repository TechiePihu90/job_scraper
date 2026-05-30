import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.db_client import db_client

async def main():
    await db_client.connect()
    if db_client.pool:
        async with db_client.pool.acquire() as conn:
            rows = await conn.fetch("SELECT company, company_slug, count(*) FROM jobs WHERE company ILIKE '%techiepihu%' GROUP BY company, company_slug")
            print(f"ILike search results: {rows}")
            if rows:
                await conn.execute("DELETE FROM jobs WHERE company ILIKE '%techiepihu%'")
                print("Deleted all jobs matching %techiepihu%")
    await db_client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
