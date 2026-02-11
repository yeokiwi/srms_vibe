"""Tests for Pydantic models."""

import pytest
from app.models import AnalysisRequest, ConfidenceLevel, ContentCategory


class TestAnalysisRequest:
    def test_normalize_url_adds_https(self):
        req = AnalysisRequest(url="example.com")
        assert req.url == "https://example.com"

    def test_normalize_url_preserves_http(self):
        req = AnalysisRequest(url="http://example.com")
        assert req.url == "http://example.com"

    def test_normalize_url_strips_trailing_slash(self):
        req = AnalysisRequest(url="https://example.com/")
        assert req.url == "https://example.com"

    def test_default_days(self):
        req = AnalysisRequest(url="https://example.com")
        assert req.days == 30

    def test_days_range_validation(self):
        with pytest.raises(Exception):
            AnalysisRequest(url="https://example.com", days=3)
        with pytest.raises(Exception):
            AnalysisRequest(url="https://example.com", days=100)

    def test_sections_default_empty(self):
        req = AnalysisRequest(url="https://example.com")
        assert req.sections == []

    def test_sections_passed(self):
        req = AnalysisRequest(url="https://example.com", sections=["/blog", "/news"])
        assert req.sections == ["/blog", "/news"]
