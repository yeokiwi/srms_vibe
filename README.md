# Website Change Analyzer

A web application that analyzes any given website to identify and report changes, updates, and announcements from a configurable time period (default: 30 days).

## Features

- **Smart crawling**: BFS crawler with robots.txt compliance, rate limiting, and configurable depth
- **Multi-source detection**: Analyzes HTML content, meta tags, HTTP headers, structured data (JSON-LD), RSS/Atom feeds, and sitemap.xml
- **Confidence levels**: Distinguishes between CONFIRMED (date-backed) and LIKELY RECENT (contextual evidence) findings
- **Content categorization**: Blog posts, product updates, pricing changes, policy updates, press releases, events, hiring, changelogs
- **Sentiment & importance**: Automatic sentiment detection and importance scoring
- **Export**: JSON, CSV, and PDF report generation
- **Real-time progress**: Async analysis with progress polling

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11+, FastAPI, httpx, BeautifulSoup4, feedparser |
| Frontend | React 18, Vite, Tailwind CSS |
| Analysis | dateutil, regex-based NLP, structured data parsing |
| Export | reportlab (PDF), csv module, JSON |

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs on `http://localhost:3000` and proxies API calls to the backend at `http://localhost:8000`.

### Running Tests

```bash
cd backend
pip install pytest
pytest -v
```

## API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for the interactive Swagger UI.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/analyze` | Start a new analysis |
| `GET` | `/api/analyze/{task_id}` | Get analysis status/results |
| `GET` | `/api/analyze/{task_id}/export/json` | Export as JSON |
| `GET` | `/api/analyze/{task_id}/export/csv` | Export as CSV |
| `GET` | `/api/analyze/{task_id}/export/pdf` | Export as PDF |
| `GET` | `/api/health` | Health check |

### Example: Start Analysis

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "days": 30, "sections": ["/blog"]}'
```

### Example: Poll Results

```bash
curl http://localhost:8000/api/analyze/{task_id}
```

## How It Works

1. **Crawl**: Starting from the target URL, the crawler discovers pages using BFS, prioritizing sections likely to contain updates (blog, news, changelog, etc.)
2. **Extract**: For each page, it extracts publication dates from meta tags, `<time>` elements, HTTP headers, structured data, RSS feeds, and sitemap entries
3. **Analyze**: Each page is checked for confirmed date evidence (explicit timestamps) and contextual evidence (temporal language patterns, URL date patterns, version numbers)
4. **Categorize**: Findings are categorized by content type, scored for sentiment and importance
5. **Report**: Results are compiled with summary statistics, timeline, and exportable in multiple formats

## Configuration

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `days` | 30 | 7-90 | Look-back period in days |
| `sections` | `[]` | - | Specific URL paths to prioritize |
| Max pages | 50 | - | Maximum pages crawled per analysis |
| Max depth | 3 | - | Maximum link depth from seed URLs |
| Request delay | 0.5s | - | Delay between requests (rate limiting) |
| Cache TTL | 1 hour | - | Results cache duration |

## Disclaimer

This tool crawls publicly available web pages and uses heuristics to detect recent changes. Results may not be 100% accurate. Always verify important findings manually. The tool respects robots.txt and implements rate limiting to be a good web citizen.
