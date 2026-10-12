"""Tests untuk ui/server.py"""

import pytest
from fastapi.testclient import TestClient
from yuna.ui.server import app, manager, current_status


class TestDashboardServer:
    """Test dashboard FastAPI server."""

    def setup_method(self):
        # Reset status
        global current_status
        from yuna.ui import server
        server.current_status = server.StatusData()

    def test_root_endpoint(self):
        """Test root endpoint returns HTML."""
        with TestClient(app) as client:
            response = client.get("/")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")

    def test_health_endpoint(self):
        """Test health check endpoint."""
        with TestClient(app) as client:
            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_status_endpoint(self):
        """Test status API endpoint."""
        with TestClient(app) as client:
            response = client.get("/api/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "transcript" in data
            assert "timestamp" in data

    def test_status_data_model(self):
        """Test StatusData model."""
        from yuna.ui.server import StatusData
        status = StatusData(status="listening", transcript="test")
        assert status.status == "listening"
        assert status.transcript == "test"
        assert "idle" in [StatusData().status]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])