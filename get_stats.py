
import asyncio
import json
from app.redis_client import redis_client
from app.models import Job

async def get_detailed_stats():
    await redis_client.connect()
    
    # 1. Total Jobs
    total = await redis_client.get_total_jobs_count()
    
    # Get all jobs to aggregate
    all_ids = await redis_client.pool.zrange("jobs:all", 0, -1)
    
    company_stats = {}
    portal_stats = {}
    
    if all_ids:
        keys = [f"job:{jid}" for jid in all_ids]
        # Batch fetch in chunks if too many (though 549 is fine)
        raw_jobs = await redis_client.pool.mget(*keys)
        
        for raw in raw_jobs:
            if not raw: continue
            job = Job.model_validate_json(raw)
            
            # Company-wise
            company_stats[job.company] = company_stats.get(job.company, 0) + 1
            
            # Portal-wise (ATS)
            portal_stats[job.source_ats] = portal_stats.get(job.source_ats, 0) + 1
            
    await redis_client.disconnect()
    
    return {
        "total_jobs": total,
        "company_wise": dict(sorted(company_stats.items(), key=lambda x: x[1], reverse=True)),
        "portal_wise": dict(sorted(portal_stats.items(), key=lambda x: x[1], reverse=True))
    }

if __name__ == "__main__":
    stats = asyncio.run(get_detailed_stats())
    print(json.dumps(stats, indent=2))
