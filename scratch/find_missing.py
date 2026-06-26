import asyncio

from app.db_client import db_client
from app.orchestrator import load_companies


async def find_missing():
    await db_client.connect()
    stats = await db_client.get_stats()
    companies_in_stats = set(stats["company_wise"].keys())

    all_companies = await load_companies()
    missing = [c for c in all_companies if c.name not in companies_in_stats]

    print(f"Total companies: {len(all_companies)}")
    print(f"Companies with jobs: {len(companies_in_stats)}")
    print(f"Missing companies: {len(missing)}")

    by_ats = {}
    for c in missing:
        by_ats[c.ats_type] = by_ats.get(c.ats_type, []) + [c.name]

    for ats, names in by_ats.items():
        print(f"\nATS: {ats} ({len(names)} missing)")
        print(f"Examples: {names[:5]}")

    await db_client.disconnect()


if __name__ == "__main__":
    asyncio.run(find_missing())
