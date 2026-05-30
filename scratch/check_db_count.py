import asyncio
import asyncpg
from app.config import settings


async def main() -> None:
    conn = await asyncpg.connect(
        host=settings.supabase_db_host,
        port=settings.supabase_db_port,
        user=settings.supabase_db_user,
        password=settings.supabase_db_password,
        database=settings.supabase_db_name,
        ssl='require',
    )
    count = await conn.fetchval('select count(*) from jobs')
    print('count', count)
    await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
