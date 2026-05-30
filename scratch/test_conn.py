import asyncio
import sys
from pathlib import Path
import asyncpg

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings


async def test():
    print("Step 1: Loading settings...")
    print(f"  Host: {settings.supabase_db_host}")
    print(f"  Port: {settings.supabase_db_port}")
    print(f"  User: {settings.supabase_db_user}")
    print(f"  DB Name: {settings.supabase_db_name}")

    print("\nStep 2: Connecting directly via asyncpg.connect()...")
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(
                host=settings.supabase_db_host,
                port=settings.supabase_db_port,
                user=settings.supabase_db_user,
                password=settings.supabase_db_password,
                database=settings.supabase_db_name,
                timeout=10.0,
            ),
            timeout=12.0,
        )
        print("[SUCCESS] Direct connection SUCCESSFUL!")
        await conn.close()
    except Exception as e:
        print(f"[FAILED] Direct connection FAILED: {e}")

    print("\nStep 3: Connecting via pool...")
    try:
        pool = await asyncpg.create_pool(
            host=settings.supabase_db_host,
            port=settings.supabase_db_port,
            user=settings.supabase_db_user,
            password=settings.supabase_db_password,
            database=settings.supabase_db_name,
            min_size=1,
            max_size=3,
            timeout=10.0,
        )
        print("[SUCCESS] Pool creation SUCCESSFUL!")
        async with pool.acquire() as conn:
            val = await conn.fetchval("SELECT NOW()")
            print(f"[SUCCESS] Query Select Now SUCCESSFUL: {val}")
        await pool.close()
    except Exception as e:
        print(f"[FAILED] Pool connection FAILED: {e}")


if __name__ == "__main__":
    asyncio.run(test())
