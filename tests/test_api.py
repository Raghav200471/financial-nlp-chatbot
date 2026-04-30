"""
API Endpoint Tests
===================
Integration tests for the FastAPI endpoints using TestClient.
"""

import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as c:
        yield c


class TestAPIEndpoints:
    """Test all API endpoints."""

    def test_root(self, client):
        """Test root endpoint returns API info."""
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data
        assert "Financial" in data["message"]

    def test_health(self, client):
        """Test health endpoint."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["models_loaded"] is True

    def test_chat_greeting(self, client):
        """Test chat with a greeting message."""
        resp = client.post("/api/chat", json={
            "message": "Hello",
            "session_id": "test_session"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert "intent" in data
        assert "session_id" in data
        assert data["session_id"] == "test_session"

    def test_chat_stock_query(self, client):
        """Test chat with a stock price query."""
        resp = client.post("/api/chat", json={
            "message": "What is the price of AAPL?",
            "session_id": "test_stock"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "get_stock_price"

    def test_chat_emi_query(self, client):
        """Test chat with an EMI calculation query."""
        resp = client.post("/api/chat", json={
            "message": "Calculate EMI for 10 lakh at 8.5% for 20 years",
            "session_id": "test_emi"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data

    def test_chat_empty_message(self, client):
        """Test that empty message is rejected."""
        resp = client.post("/api/chat", json={
            "message": "",
            "session_id": "test_empty"
        })
        assert resp.status_code == 422  # Validation error

    def test_predict_intent(self, client):
        """Test the predict-intent debug endpoint."""
        resp = client.post("/api/predict-intent", json={
            "text": "What is the price of AAPL?"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "intent" in data
        assert "confidence" in data
        assert "entities" in data
        assert data["intent"] == "get_stock_price"

    def test_chat_default_session(self, client):
        """Test chat with default session (no session_id provided)."""
        resp = client.post("/api/chat", json={
            "message": "Hi"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "default"

    def test_chat_response_has_entities(self, client):
        """Test that entities are returned in the response."""
        resp = client.post("/api/chat", json={
            "message": "Convert 100 USD to INR",
            "session_id": "test_entities"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "entities" in data
        assert isinstance(data["entities"], list)
