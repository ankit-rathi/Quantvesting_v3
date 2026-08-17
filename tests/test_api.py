import os

# Keep the beta API import deterministic for tests.
os.environ.pop("QV_ACCESS_KEY", None)

from fastapi.testclient import TestClient
from quantvesting.api.app import app


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_web_ui_is_served():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Quantvesting" in response.text
