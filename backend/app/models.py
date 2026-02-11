"""Pydantic models for request/response schemas."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ConfidenceLevel(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    LIKELY_RECENT = "LIKELY RECENT"


class ContentCategory(str, enum.Enum):
    BLOG_POST = "Blog Post"
    PRODUCT_UPDATE = "Product Update"
    FEATURE_RELEASE = "Feature Release"
    PRICING_CHANGE = "Pricing Change"
    POLICY_UPDATE = "Policy Update"
    PRESS_RELEASE = "Press Release"
    EVENT = "Event"
    HIRING = "Hiring"
    CHANGELOG = "Changelog"
    OTHER = "Other"


class Sentiment(str, enum.Enum):
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    NEGATIVE = "Negative"


class ImportanceLevel(str, enum.Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class AnalysisStatus(str, enum.Enum):
    QUEUED = "queued"
    CRAWLING = "crawling"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AnalysisRequest(BaseModel):
    url: str = Field(..., description="Website URL to analyze")
    sections: list[str] = Field(
        default_factory=list,
        description="Optional specific sections to focus on (e.g., /blog, /news)",
    )
    days: int = Field(
        default=30,
        ge=7,
        le=90,
        description="Number of days to look back (7-90)",
    )

    @field_validator("url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        # Remove trailing slash for consistency
        return v.rstrip("/")


# ---------------------------------------------------------------------------
# Finding models
# ---------------------------------------------------------------------------

class Finding(BaseModel):
    confidence: ConfidenceLevel
    category: ContentCategory
    title: str
    date: Optional[str] = None
    source_url: str
    summary: str
    evidence: list[str]
    excerpt: str
    sentiment: Sentiment = Sentiment.NEUTRAL
    importance: ImportanceLevel = ImportanceLevel.MEDIUM


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class AnalysisSummary(BaseModel):
    total_findings: int = 0
    confirmed_count: int = 0
    likely_recent_count: int = 0
    category_breakdown: dict[str, int] = Field(default_factory=dict)
    timeline: list[dict] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    task_id: str
    status: AnalysisStatus
    url: str
    days: int
    progress: float = 0.0
    progress_message: str = ""
    summary: Optional[AnalysisSummary] = None
    findings: list[Finding] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
