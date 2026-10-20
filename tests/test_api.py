"""Mocked API tests. These do not call live Tavily or Mistral APIs."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.routes import get_agent, get_repository
from app.errors import ConfigurationError, ResearchIncompleteError, UpstreamServiceError
from app.main import app
from app.schemas import (
    GenerateGuideRequest,
    GenerateGuideResponse,
    OAuthGuide,
    ResearchActivity,
)
from app.storage.repository import GuideRepository
from tests.helpers import valid_guide_payload


def _guide(guide_id: str = "guide-123") -> OAuthGuide:
    payload = valid_guide_payload()
    return OAuthGuide(
        id=guide_id,
        submitted_input="example.com",
        integration_goal="Create issues",
        generated_at=datetime.now(timezone.utc),
        research_activity=ResearchActivity(),
        **payload,
    )


class StubAgent:
    def __init__(self, result=None, error=None) -> None:
        self.result = result
        self.error = error

    def generate(self, request: GenerateGuideRequest) -> GenerateGuideResponse:
        if self.error:
            raise self.error
        return self.result


def test_library_available_without_api_keys(client):
    response = client.get("/api/library")
    assert response.status_code == 200
    body = response.json()
    names = {item["app_name"] for item in body}
    assert names == {"GitHub", "Slack", "Google Calendar"}
    for item in body:
        assert item["review_status"] == "source_review_only"
        assert item["source_links"]
        assert "official_domain" in item


def test_generate_rejects_empty_body(client):
    response = client.post("/api/guides/generate", json={"app_name_or_url": ""})
    assert response.status_code == 422


def test_generate_rejects_malformed_payload(client):
    response = client.post("/api/guides/generate", json={"app_name_or_url": 12})
    assert response.status_code == 422


def test_generate_rejects_loopback_host(client):
    class Agent(StubAgent):
        def generate(self, request: GenerateGuideRequest) -> GenerateGuideResponse:
            from app.services.input_normalizer import normalize_app_input

            normalize_app_input(request.app_name_or_url)
            raise AssertionError("should not reach live research")

    app.dependency_overrides[get_agent] = lambda: Agent()
    try:
        response = client.post("/api/guides/generate", json={"app_name_or_url": "http://127.0.0.1"})
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()


def test_generate_missing_configuration(client):
    app.dependency_overrides[get_agent] = lambda: StubAgent(
        error=ConfigurationError("Live research is disabled because required API keys are missing: MISTRAL_API_KEY")
    )
    try:
        response = client.post("/api/guides/generate", json={"app_name_or_url": "linear.app"})
        assert response.status_code == 503
        assert "MISTRAL_API_KEY" in response.text
    finally:
        app.dependency_overrides.clear()


def test_generate_success_mocked(client):
    guide = _guide()
    app.dependency_overrides[get_agent] = lambda: StubAgent(
        result=GenerateGuideResponse(
            status="complete",
            message="ok",
            guide=guide,
            research_activity=guide.research_activity,
        )
    )
    try:
        response = client.post(
            "/api/guides/generate",
            json={
                "app_name_or_url": "example.com",
                "integration_goal": "Create issues",
                "requested_scopes": [],
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "complete"
        assert body["guide"]["id"] == "guide-123"
        assert body["guide"]["testing_record"]["tested"] is False
    finally:
        app.dependency_overrides.clear()


def test_generate_upstream_error(client):
    app.dependency_overrides[get_agent] = lambda: StubAgent(
        error=UpstreamServiceError("Tavily Search timed out. Try again in a moment.")
    )
    try:
        response = client.post("/api/guides/generate", json={"app_name_or_url": "linear.app"})
        assert response.status_code == 502
    finally:
        app.dependency_overrides.clear()


def test_generate_incomplete_research(client):
    app.dependency_overrides[get_agent] = lambda: StubAgent(
        error=ResearchIncompleteError("Tavily returned no usable search results. Live research could not continue.")
    )
    try:
        response = client.post("/api/guides/generate", json={"app_name_or_url": "unknown-app-xyz"})
        assert response.status_code == 422
        assert "incomplete_research" in response.text
    finally:
        app.dependency_overrides.clear()


def test_get_guide_round_trip(tmp_path):
    repo = GuideRepository(str(tmp_path / "guides.db"))
    guide = _guide("persisted-guide")
    repo.save(guide)
    app.dependency_overrides[get_repository] = lambda: repo
    try:
        local = TestClient(app)
        missing = local.get("/api/guides/does-not-exist")
        assert missing.status_code == 404
        found = local.get("/api/guides/persisted-guide")
        assert found.status_code == 200
        assert found.json()["id"] == "persisted-guide"
        assert found.json()["testing_record"]["tested"] is False
    finally:
        app.dependency_overrides.clear()
