"""Pydantic models for job data and company configuration."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Job(BaseModel):
    """Normalized job representation across all ATS platforms."""

    job_id: str = Field(..., description="Unique job identifier (ATS-specific)")
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str = Field(..., description="Job location (US only)")
    description: str = Field(default="", description="Job description")
    posted_at: Optional[str] = Field(default=None, description="ISO-8601 posted date")
    apply_url: str = Field(..., description="Direct application URL")
    source_ats: str = Field(..., description="ATS platform name")
    scraped_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp when the job was scraped",
    )

    def to_redis_key(self) -> str:
        """Generate a deterministic Redis key for this job."""
        return f"job:{self.job_id}"

    def company_slug(self) -> str:
        """Generate a URL-safe company slug."""
        return self.company.lower().replace(" ", "-").replace(".", "").replace(",", "")


class CompanyConfig(BaseModel):
    """Configuration entry for a single company to scrape."""

    name: str = Field(..., description="Company display name")
    ats_type: str = Field(..., description="ATS platform type (greenhouse, lever, workday, ...)")
    identifier: str = Field(..., description="Company identifier on the ATS (board token, slug, tenant ID)")
    base_url: Optional[str] = Field(default=None, description="Override base URL for the ATS")
    extra: dict = Field(default_factory=dict, description="ATS-specific extra config")


class JobSearchParams(BaseModel):
    """Query parameters for the job search API endpoint."""

    keyword: Optional[str] = Field(default=None, description="Keyword search in title/description")
    location: Optional[str] = Field(default=None, description="Location filter")
    company: Optional[str] = Field(default=None, description="Company name filter")
    page: int = Field(default=1, ge=1, description="Page number")
    limit: int = Field(default=25, ge=1, le=100, description="Results per page")
