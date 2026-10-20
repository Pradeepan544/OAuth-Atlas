"""Mocked research-agent tests. These do not call Tavily or Mistral and are not provider setup tests."""

from __future__ import annotations

import logging

import httpx
import pytest

from app.config import Settings
from app.errors import ConfigurationError, GuideValidationError, ResearchIncompleteError, UpstreamServiceError
from app.schemas import EvidenceStatus, GenerateGuideRequest, GuideDraft
from app.security_logging import SecretRedactFilter, redact_text
from app.services.evidence_validator import validate_and_repair_draft
from app.services.mistral_client import MistralClient, parse_json_object
from app.services.research_agent import ResearchAgent
from app.services.tavily_search import TavilyClient
from app.storage.repository import GuideRepository
from tests.helpers import (
    FakeMistral,
    FakeTavily,
    sample_source,
    valid_guide_payload,
    valid_plan,
    valid_review,
)


def _settings(**overrides) -> Settings:
    values = dict(
        mistral_api_key="test-mistral-key",
        tavily_api_key="test-tavily-key",
        http_max_attempts=2,
    )
    values.update(overrides)
    return Settings(**values)


def _agent(tmp_path, mistral, tavily, settings=None) -> ResearchAgent:
    repo = GuideRepository(str(tmp_path / "guides.db"))
    return ResearchAgent(settings or _settings(), mistral, tavily, repo)


def test_missing_configuration_does_not_fake_success(tmp_path):
    agent = _agent(
        tmp_path,
        FakeMistral([]),
        FakeTavily([]),
        settings=_settings(mistral_api_key="", tavily_api_key=""),
    )
    with pytest.raises(ConfigurationError, match="API keys are missing"):
        agent.generate(GenerateGuideRequest(app_name_or_url="linear.app"))


def test_generate_persists_guide_with_mocked_services(tmp_path):
    mistral = FakeMistral([valid_plan(), valid_review(), valid_guide_payload()])
    tavily = FakeTavily([sample_source()])
    agent = _agent(tmp_path, mistral, tavily)
    result = agent.generate(GenerateGuideRequest(app_name_or_url="example.com", integration_goal="Create issues"))
    assert result.status == "complete"
    assert result.guide is not None
    assert result.guide.testing_record.tested is False
    loaded = agent.repository.get(result.guide.id)
    assert loaded is not None
    assert loaded.id == result.guide.id
    assert loaded.submitted_input == "example.com"


def test_invalid_mistral_json_gets_one_repair_attempt(tmp_path):
    mistral = FakeMistral(
        [
            valid_plan(),
            valid_review(),
            {"not": "a guide"},
            valid_guide_payload(),
        ]
    )
    agent = _agent(tmp_path, mistral, FakeTavily([sample_source()]))
    result = agent.generate(GenerateGuideRequest(app_name_or_url="example.com"))
    assert result.status == "complete"
    assert result.research_activity.repair_attempts == 1


def test_invalid_json_after_repair_returns_error(tmp_path):
    mistral = FakeMistral(
        [
            valid_plan(),
            valid_review(),
            {"not": "a guide"},
            {"still": "invalid"},
        ]
    )
    agent = _agent(tmp_path, mistral, FakeTavily([sample_source()]))
    with pytest.raises(GuideValidationError, match="repair attempt"):
        agent.generate(GenerateGuideRequest(app_name_or_url="example.com"))


def test_nonexistent_source_ids_are_removed_and_marked_uncertain():
    payload = valid_guide_payload()
    payload["steps"][0]["source_ids"] = ["S99"]
    payload["steps"][0]["evidence_status"] = "sourced"
    draft = GuideDraft.model_validate(payload)
    repaired = validate_and_repair_draft(draft, [sample_source("S1")])
    assert repaired.steps[0].source_ids == []
    assert repaired.steps[0].evidence_status == EvidenceStatus.unknown
    assert any("S99" not in note for note in repaired.unknowns) or repaired.unknowns


def test_false_tested_claim_is_removed():
    payload = valid_guide_payload()
    payload["testing_record"] = {"tested": True, "attempts": [], "notes": "looks tested"}
    draft = GuideDraft.model_validate(payload)
    repaired = validate_and_repair_draft(draft, [sample_source()])
    assert repaired.testing_record.tested is False


def test_empty_tavily_results_are_incomplete(tmp_path):
    agent = _agent(tmp_path, FakeMistral([valid_plan()]), FakeTavily([]))
    with pytest.raises(ResearchIncompleteError, match="no usable search results"):
        agent.generate(GenerateGuideRequest(app_name_or_url="example.com"))


def test_tavily_timeout_is_surfaced():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    tavily = TavilyClient(_settings(), client=client)
    with pytest.raises(UpstreamServiceError, match="timed out"):
        tavily.search("example oauth")


def test_mistral_timeout_is_surfaced():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    mistral = MistralClient(_settings(), client=client)
    with pytest.raises(UpstreamServiceError, match="timed out"):
        mistral.complete_json(system="sys", user="user")


def test_mistral_error_status_is_surfaced():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "upstream"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    mistral = MistralClient(_settings(http_max_attempts=1), client=client)
    with pytest.raises(UpstreamServiceError, match="Mistral returned an error"):
        mistral.complete_json(system="sys", user="user")


def test_tavily_error_status_is_surfaced():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, json={"error": "bad gateway"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    tavily = TavilyClient(_settings(http_max_attempts=1), client=client)
    with pytest.raises(UpstreamServiceError, match="Tavily Search returned an error"):
        tavily.search("example oauth")


def test_parse_json_object_rejects_non_objects():
    with pytest.raises(UpstreamServiceError):
        parse_json_object("[1, 2]")


def test_parse_json_object_accepts_fenced_json():
    parsed = parse_json_object("```json\n{\"ok\": true}\n```")
    assert parsed == {"ok": True}


def test_sqlite_round_trip(tmp_path):
    mistral = FakeMistral([valid_plan(), valid_review(), valid_guide_payload()])
    agent = _agent(tmp_path, mistral, FakeTavily([sample_source()]))
    created = agent.generate(GenerateGuideRequest(app_name_or_url="example.com")).guide
    assert created is not None
    other = GuideRepository(str(tmp_path / "guides.db"))
    loaded = other.get(created.id)
    assert loaded is not None
    assert loaded.app_name == created.app_name


def test_secret_filter_redacts_api_keys(caplog):
    logger = logging.getLogger("app.secret_test")
    logger.addFilter(SecretRedactFilter(["super-secret-key"]))
    with caplog.at_level(logging.INFO, logger="app.secret_test"):
        logger.info("Authorization Bearer super-secret-key")
    assert "super-secret-key" not in caplog.text
    assert "[REDACTED]" in caplog.text


def test_redact_helper_does_not_log_secrets():
    assert "abc123" not in redact_text("token abc123 here", ["abc123"])


def test_prompts_are_not_given_api_keys(tmp_path):
    mistral = FakeMistral([valid_plan(), valid_review(), valid_guide_payload()])
    settings = _settings(mistral_api_key="mistral-live-secret", tavily_api_key="tavily-live-secret")
    agent = _agent(tmp_path, mistral, FakeTavily([sample_source()]), settings=settings)
    agent.generate(GenerateGuideRequest(app_name_or_url="example.com"))
    blob = " ".join(call["system"] + call["user"] for call in mistral.calls)
    assert "mistral-live-secret" not in blob
    assert "tavily-live-secret" not in blob


def test_additional_search_round_is_bounded(tmp_path):
    review = valid_review()
    review["additional_searches"] = [
        {"query": "example.com oauth verification policy", "reason": "Need verification evidence"},
        {"query": "example.com oauth scopes list", "reason": "Need scope evidence"},
        {"query": "should not run", "reason": "Would exceed the cap if accepted"},
    ]
    mistral = FakeMistral([valid_plan(), review, valid_guide_payload()])
    tavily = FakeTavily([sample_source()])
    agent = _agent(tmp_path, mistral, tavily)
    result = agent.generate(GenerateGuideRequest(app_name_or_url="example.com"))
    assert result.status == "complete"
    assert result.research_activity.search_rounds == 2
    assert len(tavily.queries) <= 6
