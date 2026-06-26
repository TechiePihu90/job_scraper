import asyncio
import json

from app.db_client import db_client


async def get_detailed_stats():
    await db_client.connect()
    stats = await db_client.get_stats()
    await db_client.disconnect()
    return stats


if __name__ == "__main__":
    stats = asyncio.run(get_detailed_stats())
    print(json.dumps(stats, indent=2))
