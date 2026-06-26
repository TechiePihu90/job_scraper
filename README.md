# 🔍 Job Scraper — US Job Aggregator API

A production-grade, fully-async job scraping pipeline that collects US-based job listings from multiple ATS platforms, stores them in a PostgreSQL/Supabase database, and serves them through FastAPI.

---

## 🏗️ Architecture

```text
┌────────────────────┐     ┌───────────────┐     ┌─────────────────────┐
│  Orchestrator      │────▶│  ATS Scrapers │────▶│  Supabase / Postgres│
│  (asyncio.gather)  │     │  (multiple ATS)│    │  (primary storage)  │
└────────────────────┘     └───────────────┘     └──────────┬──────────┘
                                                             │
                                                     ┌───────▼───────┐
                                                     │   FastAPI     │
                                                     │   (serving)   │
                                                     └───────────────┘
```

**Design**: Lightweight job aggregation backend that persists jobs in a real database instead of Redis.

---

## 🚀 Quick Start

### Option 1: Local Development (Recommended)

```bash
cd job_scraper

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Copy environment example and fill in your database settings
copy .env.example .env
# Edit .env and set your Supabase / Postgres values

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open:

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Useful commands:

```bash
# Check health
curl http://localhost:8000/health

# Trigger a scrape in the background
curl -X POST http://localhost:8000/scrape

# List jobs
curl "http://localhost:8000/jobs?limit=10"
```

### Option 2: Docker

```bash
cd job_scraper

# Make sure .env exists with your database settings
copy .env.example .env

# Start the app container
docker compose up --build -d
```

Then verify:

```bash
curl http://localhost:8000/health
```

> The app container reads environment variables from .env automatically.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check for the API and database |
| GET | `/jobs` | List jobs with pagination and filters |
| GET | `/jobs/{job_id}` | Get a single job by ID |
| GET | `/jobs/company/{slug}` | Get jobs for a specific company |
| GET | `/stats` | Aggregate job statistics |
| POST | `/scrape` | Trigger a full scrape run in the background |

### Query Parameters for `GET /jobs`

| Param | Type | Default | Description |
|------|------|---------|-------------|
| `keyword` | string | — | Search in title/description |
| `location` | string | — | Filter by location |
| `company` | string | — | Filter by company name |
| `page` | int | 1 | Page number |
| `limit` | int | 25 | Results per page (max 100) |

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

---

## 🔧 Adding a New ATS Scraper

1. Create `app/scrapers/my_ats.py`
2. Extend `BaseScraper` and implement `scrape() -> list[Job]`
3. Register it in `app/scrapers/__init__.py`

```python
from app.scrapers.base import BaseScraper
from app.models import Job

class MyATSScraper(BaseScraper):
    ATS_NAME = "my_ats"

    async def scrape(self) -> list[Job]:
        data = await self._get(f"https://api.example.com/{self.company.identifier}/jobs")
        jobs = [self._parse(item) for item in data]
        return jobs
```

---

## ⚙️ Configuration

All settings are controlled via environment variables with the `JOBSCRAPER_` prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `JOBSCRAPER_SUPABASE_DB_HOST` | — | Supabase/Postgres host |
| `JOBSCRAPER_SUPABASE_DB_PORT` | `5432` | Database port |
| `JOBSCRAPER_SUPABASE_DB_USER` | `postgres` | Database username |
| `JOBSCRAPER_SUPABASE_DB_PASSWORD` | — | Database password |
| `JOBSCRAPER_SUPABASE_DB_NAME` | `postgres` | Database name |
| `JOBSCRAPER_SUPABASE_URL` | — | Supabase project URL |
| `JOBSCRAPER_SUPABASE_SERVICE_KEY` | — | Supabase service role key |
| `JOBSCRAPER_MAX_CONCURRENT_SCRAPERS` | `50` | Parallel scraper limit |
| `JOBSCRAPER_SCRAPE_INTERVAL_HOURS` | `6` | Auto-scrape interval |
| `JOBSCRAPER_RATE_LIMIT_PER_SECOND` | `5.0` | Per-domain rate limit |
| `JOBSCRAPER_USAJOBS_API_KEY` | — | USAJOBS API key |
| `JOBSCRAPER_LOG_LEVEL` | `INFO` | Logging level |

See `.env.example` for the full list.

---

## 📂 Project Structure

```text
job_scraper/
├── app/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Pydantic settings
│   ├── db_client.py         # Async Supabase/Postgres client
│   ├── models.py            # Job and CompanyConfig models
│   ├── orchestrator.py      # Concurrent scraper runner
│   ├── scrapers/
│   │   ├── base.py          # BaseScraper ABC
│   │   ├── greenhouse.py    # ✅ Greenhouse API
│   │   ├── lever.py         # ✅ Lever API
│   │   ├── workday.py       # ✅ Workday CXS API
│   │   └── ...              # Additional ATS scrapers
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
