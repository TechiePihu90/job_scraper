"""Finish first_seen_at backfill + index, resilient to connection drops."""
import asyncio, asyncpg

DB = dict(host="db.luqxesqzcafilfkbpjod.supabase.co", port=5432, user="postgres",
          password="wKs7UnJ9@FHklSDvh", database="postgres", timeout=30.0)


async def main():
    # Backfill in small batches, fresh connection each batch (survives drops).
    for attempt in range(200):
        try:
            c = await asyncpg.connect(**DB)
            await c.execute("SET statement_timeout = 0")
            remaining = await c.fetchval("SELECT count(*) FROM jobs WHERE first_seen_at IS NULL")
            if remaining == 0:
                await c.close()
                break
            await c.execute("""WITH cte AS (SELECT job_id FROM jobs WHERE first_seen_at IS NULL LIMIT 3000)
                               UPDATE jobs j SET first_seen_at = j.scraped_at FROM cte WHERE j.job_id = cte.job_id""")
            print("remaining before batch:", remaining, flush=True)
            await c.close()
        except Exception as e:
            print("batch error (retrying):", type(e).__name__, flush=True)
            await asyncio.sleep(1)

    # Create index (fast).
    for _ in range(10):
        try:
            c = await asyncpg.connect(**DB)
            await c.execute("SET statement_timeout = 0")
            await c.execute("CREATE INDEX IF NOT EXISTS idx_jobs_first_seen_at_desc ON jobs(first_seen_at DESC)")
            tot = await c.fetchval("SELECT count(*) FROM jobs")
            fs = await c.fetchval("SELECT count(first_seen_at) FROM jobs")
            idx = await c.fetchval("SELECT count(*) FROM pg_indexes WHERE indexname='idx_jobs_first_seen_at_desc'")
            print(f"DONE: first_seen_at {fs}/{tot}  index={bool(idx)}", flush=True)
            await c.close()
            return
        except Exception as e:
            print("index error (retrying):", type(e).__name__, flush=True)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
