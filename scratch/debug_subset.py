
import asyncio
import logging
import json
from app.orchestrator import run_all, load_companies
from app.config import settings

async def analyze_few():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    
    # Load all companies
    companies = await load_companies()
    print(f"Loaded {len(companies)} companies.")
    
    # Let's just try the first 10
    subset = companies[:10]
    # We can't easily pass a list of CompanyConfig to run_all because it re-loads from file.
    # So let's write a temporary small_companies.json
    small_config = {"companies": [c.model_dump() for c in subset]}
    with open("small_companies.json", "w") as f:
        json.dump(small_config, f)
        
    print("Running scrape for first 10 companies...")
    result = await run_all("small_companies.json")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(analyze_few())
