"""FastAPI application for Website Change Analyzer."""

from __future__ import annotations

import asyncio
import logging
import traceback
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .analyzer import ChangeAnalyzer
from .cache import MemoryCache
from .crawler import WebsiteCrawler
from .export import export_csv, export_json, export_pdf
from .models import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisStatus,
    AnalysisSummary,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Website Change Analyzer",
    description="Analyze websites for recent changes, updates, and announcements.",
    version="1.0.0",
)

# CORS - allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores
cache = MemoryCache(default_ttl=3600)
tasks: dict[str, AnalysisResponse] = {}

# Keep references to background tasks so they aren't garbage-collected
_background_tasks: set[asyncio.Task] = set()


# ---------------------------------------------------------------------------
# Global exception handler — prevents bare 500 responses
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {exc}"},
    )


# ---------------------------------------------------------------------------
# Helper to safely serialize a task to a JSON-safe dict
# ---------------------------------------------------------------------------

def _safe_task_dict(task: AnalysisResponse) -> dict:
    """Serialize task to a plain dict, catching any serialization errors."""
    try:
        return task.model_dump(mode="json")
    except Exception:
        # Fallback: return minimal safe data
        return {
            "task_id": task.task_id,
            "status": task.status.value if hasattr(task.status, "value") else str(task.status),
            "url": task.url,
            "days": task.days,
            "progress": task.progress,
            "progress_message": task.progress_message,
            "summary": None,
            "findings": [],
            "errors": task.errors + ["Response serialization failed"],
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }


# ---------------------------------------------------------------------------
# Background analysis runner
# ---------------------------------------------------------------------------

async def _run_analysis(task_id: str, request: AnalysisRequest) -> None:
    """Background task to run crawl + analysis."""
    task = tasks[task_id]
    task.status = AnalysisStatus.CRAWLING
    task.started_at = datetime.now(timezone.utc)

    async def progress_cb(pct: float, msg: str) -> None:
        task.progress = pct
        task.progress_message = msg

    try:
        # Check cache
        cached = cache.get(request.url, request.days, request.sections)
        if cached:
            task.findings = cached["findings"]
            task.summary = cached["summary"]
            task.status = AnalysisStatus.COMPLETE
            task.progress = 1.0
            task.progress_message = "Results loaded from cache."
            task.completed_at = datetime.now(timezone.utc)
            return

        # Crawl
        crawler = WebsiteCrawler(
            base_url=request.url,
            sections=request.sections,
        )
        await crawler.crawl(progress_callback=progress_cb)

        # Analyze
        task.status = AnalysisStatus.ANALYZING
        analyzer = ChangeAnalyzer(crawler, days=request.days)
        findings, summary = await analyzer.analyze(progress_callback=progress_cb)

        task.findings = findings
        task.summary = summary
        task.status = AnalysisStatus.COMPLETE
        task.completed_at = datetime.now(timezone.utc)

        # Cache results
        cache.set(request.url, request.days, request.sections, {
            "findings": findings,
            "summary": summary,
        })

    except BaseException as e:
        logger.exception(f"Analysis failed for {request.url}")
        task.status = AnalysisStatus.ERROR
        task.errors.append(str(e))
        task.completed_at = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/analyze")
async def start_analysis(request: AnalysisRequest):
    """Start a new website analysis. Returns a task ID for polling."""
    task_id = str(uuid.uuid4())
    task = AnalysisResponse(
        task_id=task_id,
        status=AnalysisStatus.QUEUED,
        url=request.url,
        days=request.days,
    )
    tasks[task_id] = task

    # Run in background — keep a strong reference to prevent GC
    bg_task = asyncio.create_task(_run_analysis(task_id, request))
    _background_tasks.add(bg_task)
    bg_task.add_done_callback(_background_tasks.discard)

    return JSONResponse(content=_safe_task_dict(task))


@app.get("/api/analyze/{task_id}")
async def get_analysis(task_id: str):
    """Get the status and results of an analysis task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return JSONResponse(content=_safe_task_dict(tasks[task_id]))


@app.get("/api/analyze/{task_id}/export/json")
async def export_analysis_json(task_id: str):
    """Export analysis results as JSON."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks[task_id]
    if task.status != AnalysisStatus.COMPLETE:
        raise HTTPException(status_code=400, detail="Analysis not yet complete")
    return Response(
        content=export_json(task),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=analysis-{task_id[:8]}.json"},
    )


@app.get("/api/analyze/{task_id}/export/csv")
async def export_analysis_csv(task_id: str):
    """Export analysis results as CSV."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks[task_id]
    if task.status != AnalysisStatus.COMPLETE:
        raise HTTPException(status_code=400, detail="Analysis not yet complete")
    return Response(
        content=export_csv(task.findings),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=analysis-{task_id[:8]}.csv"},
    )


@app.get("/api/analyze/{task_id}/export/pdf")
async def export_analysis_pdf(task_id: str):
    """Export analysis results as PDF report."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    task = tasks[task_id]
    if task.status != AnalysisStatus.COMPLETE:
        raise HTTPException(status_code=400, detail="Analysis not yet complete")
    try:
        pdf_bytes = export_pdf(task)
    except Exception as e:
        logger.exception("PDF export failed")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=analysis-{task_id[:8]}.pdf"},
    )
