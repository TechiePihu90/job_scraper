import redis
import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("JOBSCRAPER_REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(url)
r.flushall()
print("Redis flushed successfully")
