"""Diagnostic: analyze posted_at distribution to explain why 'last 1 hour' returns few jobs."""
import asyncio
import asyncpg

# Defaults copied verbatim from app/config.py
DB = dict(
    host="db.luqxesqzcafilfkbpjod.supabase.co",
    port=5432,
    user="postgres",
    password="wKs7UnJ9@FHklSDvh",
    database="postgres",
    timeout=30.0,
)


async def main():
    conn = await asyncpg.connect(**DB)
    print("CONNECTED to", DB["host"])

    total = await conn.fetchval("SELECT COUNT(*) FROM jobs")
    print(f"\nTOTAL jobs: {total}")

    null_posted = await conn.fetchval("SELECT COUNT(*) FROM jobs WHERE posted_at IS NULL")
    print(f"posted_at IS NULL: {null_posted}  ({100*null_posted/total:.1f}%)")
    print(f"posted_at NOT NULL: {total - null_posted}")

    # Time windows on posted_at
    print("\n--- posted_at windows (NOT NULL only) ---")
    for label, interval in [
        ("last 1 hour", "1 hour"),
        ("last 6 hours", "6 hours"),
        ("last 24 hours", "24 hours"),
        ("last 7 days", "7 days"),
        ("last 30 days", "30 days"),
    ]:
        c = await conn.fetchval(
            f"SELECT COUNT(*) FROM jobs WHERE posted_at >= now() - interval '{interval}'"
        )
        print(f"  posted_at within {label:14}: {c}")

    # Time windows on scraped_at
    print("\n--- scraped_at windows ---")
    for label, interval in [
        ("last 1 hour", "1 hour"),
        ("last 6 hours", "6 hours"),
        ("last 24 hours", "24 hours"),
        ("last 7 days", "7 days"),
    ]:
        c = await conn.fetchval(
            f"SELECT COUNT(*) FROM jobs WHERE scraped_at >= now() - interval '{interval}'"
        )
        print(f"  scraped_at within {label:14}: {c}")

    # min/max
    mn, mx = await conn.fetchrow("SELECT min(posted_at), max(posted_at) FROM jobs")
    print(f"\nposted_at min={mn}  max={mx}")
    smn, smx = await conn.fetchrow("SELECT min(scraped_at), max(scraped_at) FROM jobs")
    print(f"scraped_at min={smn}  max={smx}")
    print("DB now():", await conn.fetchval("SELECT now()"))

    # posted_at availability by ATS
    print("\n--- posted_at availability by source_ats ---")
    rows = await conn.fetch("""
        SELECT source_ats,
               COUNT(*) AS total,
               COUNT(posted_at) AS with_posted,
               COUNT(*) FILTER (WHERE posted_at >= now() - interval '1 hour') AS last_1h
        FROM jobs GROUP BY source_ats ORDER BY total DESC
    """)
    for r in rows:
        print(f"  {r['source_ats']:18} total={r['total']:5}  with_posted={r['with_posted']:5}  last_1h={r['last_1h']}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
