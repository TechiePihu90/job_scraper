import asyncio

from app.db_client import db_client


async def main():
    await db_client.connect()
    try:
        async with db_client.pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT column_name FROM information_schema.columns WHERE table_name='jobs' AND column_name='content_hash'"
            )
            print('content_hash exists:' , bool(val))
    finally:
        await db_client.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
