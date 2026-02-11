"""Change detection and content analysis engine."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from dateutil import parser as dateutil_parser

from .crawler import CrawledPage, WebsiteCrawler
from .models import (
    AnalysisSummary,
    ConfidenceLevel,
    ContentCategory,
    Finding,
    ImportanceLevel,
    Sentiment,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Temporal language patterns
# ---------------------------------------------------------------------------

TEMPORAL_PATTERNS = [
    (r"\b(just\s+launched|just\s+released|just\s+announced)\b", "Contains phrase indicating recent launch"),
    (r"\b(new\s+feature|newly\s+added|brand\s+new)\b", "Contains phrase indicating new addition"),
    (r"\b(recently\s+updated|recently\s+added|recently\s+released)\b", "Contains phrase indicating recent update"),
    (r"\b(this\s+month|this\s+week|today)\b", "Contains temporal reference to current period"),
    (r"\b(now\s+available|now\s+live|coming\s+soon)\b", "Contains availability announcement language"),
    (r"\b(introducing|announcing|we.re\s+excited)\b", "Contains announcement language"),
    (r"\b(v\d+\.\d+|version\s+\d+)\b", "Contains version number reference"),
    (r"\bupdated?\b", "Contains 'update' keyword"),
    (r"\blatest\b", "Contains 'latest' keyword"),
]

# Category detection patterns
CATEGORY_PATTERNS = {
    ContentCategory.BLOG_POST: [r"/blog/", r"/article/", r"/post/", r"blog\."],
    ContentCategory.PRODUCT_UPDATE: [r"/product", r"/feature", r"/update", r"/release"],
    ContentCategory.CHANGELOG: [r"/changelog", r"/changes", r"/release-notes", r"/what.?s.?new"],
    ContentCategory.PRICING_CHANGE: [r"/pricing", r"/plans", r"/subscription"],
    ContentCategory.POLICY_UPDATE: [r"/privacy", r"/terms", r"/tos", r"/legal", r"/policy", r"/gdpr"],
    ContentCategory.PRESS_RELEASE: [r"/press", r"/media", r"/pr/"],
    ContentCategory.EVENT: [r"/event", r"/conference", r"/webinar", r"/meetup"],
    ContentCategory.HIRING: [r"/career", r"/job", r"/hiring", r"/join", r"/team"],
}

# Year/month URL pattern
DATE_URL_PATTERN = re.compile(r"/(\d{4})/(\d{1,2})/")

# Current year for copyright checks
CURRENT_YEAR = datetime.now().year


def _parse_date(date_str: str) -> Optional[datetime]:
    """Try to parse a date string into a datetime object."""
    if not date_str:
        return None
    try:
        return dateutil_parser.parse(date_str, fuzzy=True)
    except (ValueError, OverflowError):
        return None


def _is_within_range(date: Optional[datetime], days: int) -> bool:
    """Check if a date is within the specified number of days from now."""
    if not date:
        return False
    now = datetime.now(timezone.utc)
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    cutoff = now - timedelta(days=days)
    return date >= cutoff


def _detect_category(url: str, text: str) -> ContentCategory:
    """Detect content category from URL and text patterns."""
    url_lower = url.lower()
    text_lower = text.lower()[:1000]

    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url_lower) or re.search(pattern, text_lower):
                return category

    return ContentCategory.OTHER


def _detect_sentiment(text: str) -> Sentiment:
    """Simple sentiment detection based on keyword analysis."""
    text_lower = text.lower()
    positive_words = [
        "excited", "happy", "great", "amazing", "improved", "better",
        "new feature", "launch", "introducing", "pleased", "delighted",
        "enhanced", "faster", "easier", "powerful",
    ]
    negative_words = [
        "deprecated", "removed", "discontinued", "breaking change",
        "end of life", "sunset", "price increase", "downtime",
        "incident", "outage", "vulnerability", "security issue",
    ]
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)

    if pos_count > neg_count:
        return Sentiment.POSITIVE
    elif neg_count > pos_count:
        return Sentiment.NEGATIVE
    return Sentiment.NEUTRAL


def _detect_importance(finding: Finding) -> ImportanceLevel:
    """Estimate importance level of a finding."""
    text_lower = (finding.title + " " + finding.summary).lower()

    high_indicators = [
        "pricing", "security", "breaking", "major", "critical",
        "deprecat", "policy", "terms of service", "privacy",
    ]
    low_indicators = [
        "minor", "patch", "typo", "small", "cosmetic",
    ]

    for word in high_indicators:
        if word in text_lower:
            return ImportanceLevel.HIGH
    for word in low_indicators:
        if word in text_lower:
            return ImportanceLevel.LOW

    if finding.confidence == ConfidenceLevel.CONFIRMED:
        return ImportanceLevel.MEDIUM
    return ImportanceLevel.LOW


def _extract_summary(text: str, max_length: int = 200) -> str:
    """Extract a clean text excerpt."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_length:
        return text
    # Try to break at a sentence boundary
    truncated = text[:max_length]
    last_period = truncated.rfind(".")
    if last_period > max_length // 2:
        return truncated[: last_period + 1]
    return truncated + "..."


def _extract_date_from_html(page: CrawledPage) -> Optional[str]:
    """Try to extract publication date from HTML content."""
    if not page.soup:
        return None

    # Check common date elements
    date_selectors = [
        {"name": "time", "attr": "datetime"},
        {"name": "time", "attr": None},
        {"class_": re.compile(r"date|time|published|posted", re.I)},
    ]

    # Check <time> elements
    for time_tag in page.soup.find_all("time"):
        dt = time_tag.get("datetime")
        if dt:
            return dt
        text = time_tag.get_text(strip=True)
        if text:
            parsed = _parse_date(text)
            if parsed:
                return text

    # Check elements with date-like classes
    for elem in page.soup.find_all(class_=re.compile(r"(date|time|publish|posted)", re.I)):
        text = elem.get_text(strip=True)
        if text and len(text) < 50:
            parsed = _parse_date(text)
            if parsed:
                return text

    return None


class ChangeAnalyzer:
    """Analyze crawled pages for recent changes."""

    def __init__(self, crawler: WebsiteCrawler, days: int = 30):
        self.crawler = crawler
        self.days = days
        self.findings: list[Finding] = []
        self._seen_urls: set[str] = set()

    def _add_finding(self, finding: Finding) -> None:
        """Add a finding if its URL hasn't been seen yet."""
        if finding.source_url not in self._seen_urls:
            finding.importance = _detect_importance(finding)
            self._seen_urls.add(finding.source_url)
            self.findings.append(finding)

    def _analyze_page_dates(self, page: CrawledPage) -> None:
        """Check for confirmed date-based evidence."""
        evidence: list[str] = []
        found_date: Optional[str] = None
        is_recent = False

        # 1. Check publication date from meta tags
        if page.publication_date:
            parsed = _parse_date(page.publication_date)
            if parsed and _is_within_range(parsed, self.days):
                evidence.append(f"Published date: {page.publication_date}")
                found_date = page.publication_date
                is_recent = True

        # 2. Check Last-Modified header
        if page.last_modified:
            parsed = _parse_date(page.last_modified)
            if parsed and _is_within_range(parsed, self.days):
                evidence.append(f"Last-Modified header: {page.last_modified}")
                if not found_date:
                    found_date = page.last_modified
                is_recent = True

        # 3. Check HTML date elements
        html_date = _extract_date_from_html(page)
        if html_date:
            parsed = _parse_date(html_date)
            if parsed and _is_within_range(parsed, self.days):
                evidence.append(f"HTML date element: {html_date}")
                if not found_date:
                    found_date = html_date
                is_recent = True

        # 4. Check structured data
        for sd in page.structured_data:
            for key in ["datePublished", "dateModified", "dateCreated"]:
                if key in sd:
                    parsed = _parse_date(sd[key])
                    if parsed and _is_within_range(parsed, self.days):
                        evidence.append(f"Structured data {key}: {sd[key]}")
                        if not found_date:
                            found_date = sd[key]
                        is_recent = True

        if is_recent:
            category = _detect_category(page.url, page.text_content)
            sentiment = _detect_sentiment(page.text_content)
            self._add_finding(Finding(
                confidence=ConfidenceLevel.CONFIRMED,
                category=category,
                title=page.title or page.url,
                date=found_date,
                source_url=page.url,
                summary=_extract_summary(page.text_content),
                evidence=evidence,
                excerpt=page.text_content[:200],
                sentiment=sentiment,
            ))

    def _analyze_page_contextual(self, page: CrawledPage) -> None:
        """Check for contextual (likely recent) evidence."""
        if page.url in self._seen_urls:
            return

        evidence: list[str] = []
        text = page.text_content

        # 1. Temporal language patterns
        for pattern, description in TEMPORAL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                evidence.append(description)

        # 2. URL date patterns
        url_match = DATE_URL_PATTERN.search(page.url)
        if url_match:
            year, month = int(url_match.group(1)), int(url_match.group(2))
            try:
                url_date = datetime(year, month, 1, tzinfo=timezone.utc)
                if _is_within_range(url_date, self.days):
                    evidence.append(f"URL contains /{year}/{month:02d}/ pattern")
            except ValueError:
                pass

        # 3. Copyright year check
        copyright_match = re.search(r"©\s*(\d{4})|copyright\s+(\d{4})", text, re.IGNORECASE)
        if copyright_match:
            year = int(copyright_match.group(1) or copyright_match.group(2))
            if year == CURRENT_YEAR:
                evidence.append(f"Copyright year matches current year ({CURRENT_YEAR})")

        if evidence:
            category = _detect_category(page.url, text)
            sentiment = _detect_sentiment(text)
            self._add_finding(Finding(
                confidence=ConfidenceLevel.LIKELY_RECENT,
                category=category,
                title=page.title or page.url,
                date=None,
                source_url=page.url,
                summary=_extract_summary(text),
                evidence=evidence,
                excerpt=text[:200],
                sentiment=sentiment,
            ))

    def _analyze_rss_feeds(self) -> None:
        """Analyze RSS feed entries for recent content."""
        for entry in self.crawler.rss_feeds:
            if not entry.get("published"):
                continue
            parsed = _parse_date(entry["published"])
            if parsed and _is_within_range(parsed, self.days):
                url = entry.get("link", "")
                self._add_finding(Finding(
                    confidence=ConfidenceLevel.CONFIRMED,
                    category=_detect_category(url, entry.get("title", "")),
                    title=entry.get("title", "RSS Feed Entry"),
                    date=entry["published"],
                    source_url=url,
                    summary=_extract_summary(entry.get("summary", "")),
                    evidence=[f"RSS feed published date: {entry['published']}"],
                    excerpt=entry.get("summary", "")[:200],
                    sentiment=_detect_sentiment(entry.get("summary", "")),
                ))

    def _analyze_sitemap(self) -> None:
        """Analyze sitemap entries for recent modifications."""
        for entry in self.crawler.sitemap_entries:
            lastmod = entry.get("lastmod")
            if not lastmod:
                continue
            parsed = _parse_date(lastmod)
            if parsed and _is_within_range(parsed, self.days):
                url = entry["url"]
                if url not in self._seen_urls:
                    self._add_finding(Finding(
                        confidence=ConfidenceLevel.CONFIRMED,
                        category=_detect_category(url, ""),
                        title=url.split("/")[-1].replace("-", " ").title() or url,
                        date=lastmod,
                        source_url=url,
                        summary=f"Page listed in sitemap with recent modification date: {lastmod}",
                        evidence=[f"Sitemap lastmod: {lastmod}"],
                        excerpt="",
                        sentiment=Sentiment.NEUTRAL,
                    ))

    def _build_summary(self) -> AnalysisSummary:
        """Build analysis summary from findings."""
        confirmed = sum(1 for f in self.findings if f.confidence == ConfidenceLevel.CONFIRMED)
        likely = sum(1 for f in self.findings if f.confidence == ConfidenceLevel.LIKELY_RECENT)

        category_breakdown: dict[str, int] = {}
        for f in self.findings:
            key = f.category.value
            category_breakdown[key] = category_breakdown.get(key, 0) + 1

        # Build timeline
        timeline: list[dict] = []
        for f in self.findings:
            if f.date:
                parsed = _parse_date(f.date)
                if parsed:
                    timeline.append({
                        "date": parsed.strftime("%Y-%m-%d"),
                        "title": f.title,
                        "category": f.category.value,
                        "confidence": f.confidence.value,
                    })
        timeline.sort(key=lambda x: x["date"], reverse=True)

        return AnalysisSummary(
            total_findings=len(self.findings),
            confirmed_count=confirmed,
            likely_recent_count=likely,
            category_breakdown=category_breakdown,
            timeline=timeline,
        )

    async def analyze(self, progress_callback=None) -> tuple[list[Finding], AnalysisSummary]:
        """Run full analysis on crawled pages."""
        if progress_callback:
            await progress_callback(0.6, "Analyzing pages for date evidence...")

        # Analyze each page
        total = len(self.crawler.pages)
        for i, page in enumerate(self.crawler.pages):
            if page.status_code == 200:
                self._analyze_page_dates(page)
                self._analyze_page_contextual(page)

            if progress_callback and total > 0:
                pct = 0.6 + (0.2 * (i + 1) / total)
                await progress_callback(pct, f"Analyzed {i + 1}/{total} pages...")

        if progress_callback:
            await progress_callback(0.85, "Analyzing RSS feeds...")

        # Analyze RSS feeds
        self._analyze_rss_feeds()

        if progress_callback:
            await progress_callback(0.9, "Analyzing sitemap...")

        # Analyze sitemap
        self._analyze_sitemap()

        if progress_callback:
            await progress_callback(0.95, "Building summary...")

        # Sort findings: confirmed first, then by date
        self.findings.sort(key=lambda f: (
            0 if f.confidence == ConfidenceLevel.CONFIRMED else 1,
            f.date or "",
        ), reverse=False)
        # Actually reverse so newest confirmed are first
        confirmed = [f for f in self.findings if f.confidence == ConfidenceLevel.CONFIRMED]
        likely = [f for f in self.findings if f.confidence == ConfidenceLevel.LIKELY_RECENT]
        confirmed.sort(key=lambda f: f.date or "", reverse=True)
        self.findings = confirmed + likely

        summary = self._build_summary()

        if progress_callback:
            await progress_callback(1.0, "Analysis complete.")

        return self.findings, summary
