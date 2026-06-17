"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration for the job scraper system."""

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    redis_max_connections: int = Field(default=50, description="Max Redis connection pool size")

    # Scraping
    job_ttl_seconds: int = Field(default=86400, description="TTL for job keys in Redis (24h)")
    max_concurrent_scrapers: int = Field(default=50, description="Max concurrent scraper tasks")
    scrape_it_only: bool = Field(default=False, description="Whether to filter for IT titles only")
    scrape_interval_hours: int = Field(default=6, description="Hours between scheduled scrapes")
    request_timeout_seconds: int = Field(default=30, description="HTTP request timeout")
    max_retries: int = Field(default=3, description="Max retries per request")
    retry_base_delay: float = Field(default=1.0, description="Base delay in seconds for exponential backoff")

    # Rate limiting
    rate_limit_per_second: float = Field(default=5.0, description="Requests per second per domain")

    # API
    api_host: str = Field(default="0.0.0.0", description="FastAPI host")
    api_port: int = Field(default=8000, description="FastAPI port")
    api_default_page_size: int = Field(default=25, description="Default pagination size")
    api_max_page_size: int = Field(default=100, description="Max pagination size")

    # External API keys
    usajobs_api_key: str = Field(default="", description="USAJOBS API key")
    usajobs_user_agent: str = Field(default="", description="USAJOBS required User-Agent (email)")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Config file
    companies_config_path: str = Field(default="companies.json", description="Path to companies config")

    # Supabase / Postgres Database
    supabase_db_host: str = Field(default="db.luqxesqzcafilfkbpjod.supabase.co", description="Supabase DB Host")
    supabase_db_port: int = Field(default=5432, description="Supabase DB Port")
    supabase_db_user: str = Field(default="postgres", description="Supabase DB User")
    supabase_db_password: str = Field(default="wKs7UnJ9@FHklSDvh", description="Supabase DB Password")
    supabase_db_name: str = Field(default="postgres", description="Supabase DB Name")
    supabase_url: str = Field(default="https://luqxesqzcafilfkbpjod.supabase.co", description="Supabase Web URL")
    supabase_service_key: str = Field(
        default="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx1cXhlc3F6Y2FmaWxma2Jwam9kIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3OTEwMDM3NywiZXhwIjoyMDk0Njc2Mzc3fQ.H9fEUj9_XlabayyO_yFyDDlMWRtxpjeJo6p5mqYaFQo",
        description="Supabase service role JWT key",
    )

    model_config = {"env_prefix": "JOBSCRAPER_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
