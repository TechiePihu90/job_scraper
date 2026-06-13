"""Run a real scrape (all companies) writing to Supabase. Redis cache stubbed (not available locally)."""
import asyncio
import json
import logging

from app.redis_client import redis_client

# Stub out Redis cache so the pipeline runs without a Redis server.
async def _noop_connect():
    return None
async def _noop_store(jobs):
    return 0
redis_client.connect = _noop_connect          # type: ignore
redis_client.store_jobs = _noop_store          # type: ignore

from app.orchestrator import run_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

if __name__ == "__main__":
    result = asyncio.run(run_all())
    print("\n==== SCRAPE SUMMARY ====")
    print(json.dumps(result, indent=2))
