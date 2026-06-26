"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration for the job scraper system."""

    model_config = SettingsConfigDict(
        env_prefix="JOBSCRAPER_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Scraping
    max_concurrent_scrapers: int = Field(default=50, description="Max concurrent scraper tasks")
    scrape_it_only: bool = Field(default=False, description="Whether to filter for IT titles only")
    scrape_interval_hours: int = Field(default=6, description="Hours between scheduled scrapes")
    request_timeout_seconds: int = Field(default=30, description="HTTP request timeout")
    max_retries: int = Field(default=3, description="Max retries per request")
    retry_base_delay: float = Field(default=1.0, description="Base delay in seconds for exponential backoff")
    job_ttl_seconds: int = Field(default=86400, description="How long a job stays valid before expiring")
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
    supabase_db_host: str = Field(default="", description="Supabase DB Host")
    supabase_db_port: int = Field(default=5432, description="Supabase DB Port")
    supabase_db_user: str = Field(default="", description="Supabase DB User")
    supabase_db_password: str = Field(default="", description="Supabase DB Password")
    supabase_db_name: str = Field(default="", description="Supabase DB Name")
    supabase_url: str = Field(default="", description="Supabase Web URL")
    supabase_service_key: str = Field(default="", description="Supabase service role JWT key")
    
    #Email alerts
    resend_api_key: str = Field(default="", description="Resend API key")
    alert_email_to: str = Field(default="", description="Receiver email address")


settings = Settings()