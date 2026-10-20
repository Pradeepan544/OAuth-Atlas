import pytest
from pydantic import ValidationError

from app.schemas import GenerateGuideRequest, GuideDraft
from app.services.input_normalizer import normalize_app_input
from app.services.source_utils import classify_source, deduplicate_sources
from app.errors import InvalidRequestError
from app.schemas import Source, SourceType
from tests.helpers import sample_source, valid_guide_payload


def test_generate_request_accepts_optional_fields():
    payload = GenerateGuideRequest(app_name_or_url="linear.app")
    assert payload.integration_goal is None
    assert payload.requested_scopes == []


def test_generate_request_rejects_empty_name():
    with pytest.raises(ValidationError):
        GenerateGuideRequest(app_name_or_url="   ")


def test_generate_request_rejects_long_scope():
    with pytest.raises(ValidationError):
        GenerateGuideRequest(app_name_or_url="Linear", requested_scopes=["x" * 121])


def test_normalize_url_extracts_hostname():
    normalized = normalize_app_input("https://linear.app/docs")
    assert normalized.hostname == "linear.app"
    assert normalized.input_kind == "url"


def test_normalize_rejects_loopback():
    with pytest.raises(InvalidRequestError):
        normalize_app_input("http://127.0.0.1/oauth")


def test_source_deduplication_by_url():
    sources = [
        sample_source("S1", "https://docs.example.com/oauth"),
        sample_source("S2", "https://docs.example.com/oauth/"),
        sample_source("S3", "https://help.example.com/oauth"),
    ]
    unique = deduplicate_sources(sources)
    assert len(unique) == 2


def test_source_not_official_just_because_title_looks_authoritative():
    source_type = classify_source("https://random-blog.example.net/ultimate-oauth-guide", "linear.app")
    assert source_type == SourceType.secondary


def test_guide_draft_schema_accepts_unknown_approval_wait():
    payload = valid_guide_payload()
    draft = GuideDraft.model_validate(payload)
    assert draft.time_estimate.approval_wait.status.value == "unknown"
