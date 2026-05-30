# 🔍 Job Scraper — US Job Aggregator API

A production-grade, fully-async job scraping pipeline that collects US-based job listings from multiple ATS platforms, stores them in **Redis** for blazing-fast retrieval, and serves them via **FastAPI**.

---

## 🏗️ Architecture

```
┌────────────────────┐     ┌───────────────┐     ┌───────────┐
│  Orchestrator      │────▶│  ATS Scrapers │────▶│   Redis   │
│  (asyncio.gather)  │     │  (13 ATS)     │     │  (primary │
│                    │     │               │     │   store)  │
└────────────────────┘     └───────────────┘     └─────┬─────┘
                                                       │
                                                 ┌─────▼─────┐
                                                 │  FastAPI   │
                                                 │  (serving) │
                                                 └───────────┘
```

**Design**: Lightweight job aggregator backend optimized for speed and frequent refresh — no traditional DB, just Redis with TTL-based auto-expiry.

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and enter the project
cd job_scraper

# Copy env file
cp .env.example .env

# Start Redis + App
docker-compose up -d

# Check health
curl m

# Trigger a scrape
curl -X POST http://localhost:8000/jobs

# Browse jobs
curljobs?limit=10
```

### Option 2: Local Development

```bash
cd job_scraper

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy env file
cp .env.example .env
# Edit .env — set JOBSCRAPER_REDIS_URL if Redis isn't on localhost

# Start Redis (must be running on localhost:6379)
# On Windows: use Docker or download Redis for Windows
docker run -d -p 6379:6379 redis:7-alpine

# Run the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Open Swagger docs
# http://localhost:8000/docs
```

---

## 📡 API Endpoints

| Method | Endpoint                    | Description                                   |
|--------|-----------------------------|-----------------------------------------------|
| GET    | `/health`                   | Health check (Redis connectivity)             |
| GET    | `/jobs`                     | List all jobs (pagination + filters)          |
| GET    | `/jobs/{job_id}`            | Get a single job by ID                        |
| GET    | `/jobs/company/{slug}`      | Get jobs for a specific company               |
| GET    | `/stats`                    | Aggregate job statistics                      |
| POST   | `/scrape`                   | Manually trigger a full scrape run            |

### Query Parameters for `GET /jobs`

| Param      | Type   | Default | Description                  |
|------------|--------|---------|------------------------------|
| `keyword`  | string | —       | Search in title/description  |
| `location` | string | —       | Filter by location           |
| `company`  | string | —       | Filter by company name       |
| `page`     | int    | 1       | Page number                  |
| `limit`    | int    | 25      | Results per page (max 100)   |

---

## 🏢 Adding Companies

Edit `companies.json`:

```json
{
  "companies": [
    {
      "name": "Company Name",
      "ats_type": "greenhouse",
      "identifier": "board-token"
    },
    {
      "name": "Another Corp",
      "ats_type": "workday",
      "identifier": "tenant/site_path",
      "base_url": "https://company.wd5.myworkdayjobs.com"
    }
  ]
}
```

### Supported ATS Types

| ATS             | Status      | Identifier Format               |
|-----------------|-------------|----------------------------------|
| `greenhouse`    | ✅ Working  | Board token (e.g., `airbnb`)    |
| `lever`         | ✅ Working  | Company slug (e.g., `netflix`)  |
| `workday`       | ✅ Working  | `tenant/site_path` + `base_url` |
| `icims`         | working      | Portal slug                     |
| `taleo`         | 🔲 Scaffold | Section slug                    |
| `successfactors`| 🔲 Scaffold | Instance ID                     |
| `smartrecruiters`| 🔲 Scaffold | Company ID                     |
| `jobvite`       | 🔲 Scaffold | Company slug                    |
| `bamboohr`      | 🔲 Scaffold | Subdomain                       |
| `jazzhr`        | 🔲 Scaffold | API key                         |
| `zoho_recruit`  | 🔲 Scaffold | Portal ID                       |
| `clearcompany`  | 🔲 Scaffold | Client slug                     |
| `usajobs`       | 🔲 Scaffold | `usajobs` (uses API key)        |

---

## 🔧 Adding a New ATS Scraper

1. Create `app/scrapers/my_ats.py`
2. Extend `BaseScraper` and implement `scrape() -> list[Job]`
3. Register in `app/scrapers/__init__.py`

```python
from app.scrapers.base import BaseScraper
from app.models import Job

class MyATSScraper(BaseScraper):
    ATS_NAME = "my_ats"

    async def scrape(self) -> list[Job]:
        # Use self._get() / self._post() for rate-limited, retry-enabled HTTP
        data = await self._get(f"https://api.example.com/{self.company.identifier}/jobs")
        jobs = [self._parse(item) for item in data]
        return jobs
```

---

## ⚙️ Configuration

All settings are controlled via environment variables (prefix: `JOBSCRAPER_`):

| Variable                            | Default                  | Description                     |
|-------------------------------------|--------------------------|---------------------------------|
| `JOBSCRAPER_REDIS_URL`              | `redis://localhost:6379/0` | Redis connection URL          |
| `JOBSCRAPER_JOB_TTL_SECONDS`        | `86400`                  | Job auto-expiry (24h)           |
| `JOBSCRAPER_MAX_CONCURRENT_SCRAPERS`| `50`                     | Parallel scraper limit          |
| `JOBSCRAPER_SCRAPE_INTERVAL_HOURS`  | `6`                      | Auto-scrape interval            |
| `JOBSCRAPER_RATE_LIMIT_PER_SECOND`  | `5.0`                    | Per-domain rate limit           |
| `JOBSCRAPER_USAJOBS_API_KEY`        | —                        | USAJOBS API key                 |
| `JOBSCRAPER_LOG_LEVEL`              | `INFO`                   | Logging level                   |

See `.env.example` for the full list.

---

## 🗄️ Redis Key Structure

```
job:{job_id}                → JSON string (TTL: 24h)
company:{company-slug}:jobs → SET of job_id strings
jobs:all                    → SORTED SET (score = timestamp)
```

---

## 📂 Project Structure

```
job_scraper/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Pydantic settings
│   ├── models.py            # Job, CompanyConfig models
│   ├── redis_client.py      # Async Redis client
│   ├── orchestrator.py      # Concurrent scraper runner
│   ├── scheduler.py         # APScheduler cron
│   ├── scrapers/
│   │   ├── base.py          # BaseScraper ABC
│   │   ├── greenhouse.py    # ✅ Greenhouse API
│   │   ├── lever.py         # ✅ Lever API
│   │   ├── workday.py       # ✅ Workday CXS API
│   │   └── ...              # 10 more scaffold scrapers
│   └── utils/
│       ├── location.py      # US location filter
│       ├── retry.py         # Exponential backoff
│       └── rate_limiter.py  # Token-bucket limiter
├── companies.json           # Company config
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 📜 License

MIT
