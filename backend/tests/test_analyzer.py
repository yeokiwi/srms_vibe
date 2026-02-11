"""Tests for the analysis engine."""

import pytest
from datetime import datetime, timezone, timedelta

from app.analyzer import (
    _parse_date,
    _is_within_range,
    _detect_category,
    _detect_sentiment,
    _extract_summary,
)
from app.models import ContentCategory, Sentiment


class TestParseDate:
    def test_iso_format(self):
        d = _parse_date("2025-01-15T12:00:00Z")
        assert d is not None
        assert d.year == 2025

    def test_human_format(self):
        d = _parse_date("January 15, 2025")
        assert d is not None
        assert d.month == 1

    def test_invalid_returns_none(self):
        assert _parse_date("not-a-date") is None
        assert _parse_date("") is None


class TestIsWithinRange:
    def test_recent_date(self):
        recent = datetime.now(timezone.utc) - timedelta(days=5)
        assert _is_within_range(recent, 30) is True

    def test_old_date(self):
        old = datetime.now(timezone.utc) - timedelta(days=60)
        assert _is_within_range(old, 30) is False

    def test_none_date(self):
        assert _is_within_range(None, 30) is False


class TestDetectCategory:
    def test_blog_url(self):
        assert _detect_category("https://example.com/blog/post", "") == ContentCategory.BLOG_POST

    def test_pricing_url(self):
        assert _detect_category("https://example.com/pricing", "") == ContentCategory.PRICING_CHANGE

    def test_privacy_url(self):
        assert _detect_category("https://example.com/privacy-policy", "") == ContentCategory.POLICY_UPDATE

    def test_unknown_url(self):
        assert _detect_category("https://example.com/about", "") == ContentCategory.OTHER


class TestDetectSentiment:
    def test_positive(self):
        assert _detect_sentiment("We're excited to introduce a new feature!") == Sentiment.POSITIVE

    def test_negative(self):
        assert _detect_sentiment("This feature has been deprecated and removed.") == Sentiment.NEGATIVE

    def test_neutral(self):
        assert _detect_sentiment("The company is located in New York.") == Sentiment.NEUTRAL


class TestExtractSummary:
    def test_short_text(self):
        assert _extract_summary("Short text.") == "Short text."

    def test_long_text_sentence_break(self):
        text = "First sentence. " + "A" * 200
        result = _extract_summary(text, max_length=200)
        assert len(result) <= 210

    def test_long_text_truncation(self):
        text = "A" * 500
        result = _extract_summary(text, max_length=200)
        assert result.endswith("...")
