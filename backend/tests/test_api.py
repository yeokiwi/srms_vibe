"""Tests for the FastAPI API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestHealthEndpoint:
    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestAnalyzeEndpoint:
    def test_start_analysis_returns_task_id(self):
        resp = client.post("/api/analyze", json={
            "url": "https://example.com",
            "days": 30,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "task_id" in data
        assert data["status"] in ("queued", "crawling", "analyzing", "complete", "error")
        assert data["url"] == "https://example.com"

    def test_start_analysis_normalizes_url(self):
        resp = client.post("/api/analyze", json={
            "url": "example.com",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://example.com"

    def test_get_analysis_not_found(self):
        resp = client.get("/api/analyze/nonexistent-id")
        assert resp.status_code == 404

    def test_get_analysis_exists(self):
        # Start an analysis first
        start_resp = client.post("/api/analyze", json={
            "url": "https://example.com",
        })
        task_id = start_resp.json()["task_id"]

        resp = client.get(f"/api/analyze/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id


class TestExportEndpoints:
    def test_export_not_found(self):
        resp = client.get("/api/analyze/nonexistent/export/json")
        assert resp.status_code == 404

    def test_export_not_complete(self):
        start_resp = client.post("/api/analyze", json={
            "url": "https://httpbin.org",
        })
        task_id = start_resp.json()["task_id"]
        # Immediately try to export (likely not complete yet)
        resp = client.get(f"/api/analyze/{task_id}/export/json")
        # Could be 400 (not complete) or 200 (if cached/fast)
        assert resp.status_code in (200, 400)
