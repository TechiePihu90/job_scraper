import asyncio
from app.db_client import db_client

async def main():
    await db_client.connect()
    try:
        async with db_client.pool.acquire() as conn:
            rows = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_name='jobs' ORDER BY ordinal_position")
            print([r['column_name'] for r in rows])
    finally:
        await db_client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
