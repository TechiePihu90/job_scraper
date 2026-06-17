"""Run DB initialization to create/alter tables and indexes.

This script connects using app.db_client and calls init_db().
"""
import asyncio

from app.db_client import db_client


async def main():
    await db_client.connect()
    try:
        await db_client.init_db()
    finally:
        await db_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
