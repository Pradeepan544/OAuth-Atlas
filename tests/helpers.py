from __future__ import annotations

from app.errors import UpstreamServiceError
from app.schemas import Source, SourceType


def sample_source(source_id: str = "S1", url: str = "https://docs.example.com/oauth") -> Source:
    return Source(
        id=source_id,
        title="Example OAuth docs",
        url=url,
        domain="docs.example.com",
        source_type=SourceType.official,
        evidence_snippet="Create an OAuth application in the developer portal and set a redirect URL.",
        relevance=0.9,
    )


def valid_plan() -> dict:
    return {
        "likely_app_name": "Example",
        "candidate_official_domain": "example.com",
        "identity_confidence": "high",
        "identity_rationale": "The user supplied example.com.",
        "search_queries": [
            "example.com OAuth developer documentation",
            "example.com create OAuth app redirect URI",
            "example.com OAuth scopes permissions",
            "example.com app verification review",
        ],
        "research_objectives": [
            "Find official app registration steps",
            "Find OAuth configuration and scopes",
            "Check verification requirements",
        ],
        "uncertainties": ["Approval wait is unknown"],
        "clarification_needed": False,
        "clarification_question": None,
    }


def valid_review() -> dict:
    return {
        "unanswered_questions": ["Exact approval wait is not documented in retrieved snippets."],
        "additional_searches": [],
        "sufficient_to_identify_app": True,
        "notes": "Official-looking documentation describes app creation and redirect URLs.",
    }


def valid_guide_payload() -> dict:
    return {
        "app_name": "Example",
        "official_domain": "example.com",
        "oauth_type": "oauth2",
        "summary": "Register an OAuth app in the Example developer portal, then configure a redirect URL.",
        "difficulty": "moderate",
        "difficulty_reason": "A developer must create credentials and handle a client secret, but no extra review was evidenced.",
        "time_estimate": {
            "hands_on_minutes_min": 20,
            "hands_on_minutes_max": 60,
            "kind": "estimate",
            "confidence": "low",
            "rationale": "Estimate based on typical app-registration flows described in retrieved docs, not a timed trial.",
            "approval_wait": {
                "status": "unknown",
                "documented_range": None,
                "notes": "No approval timeline appeared in the retrieved sources.",
            },
        },
        "prerequisites": [
            {
                "item": "An Example developer account",
                "required": True,
                "notes": None,
                "source_ids": ["S1"],
                "evidence_status": "sourced",
            }
        ],
        "steps": [
            {
                "order": 1,
                "title": "Open the developer portal",
                "instructions": "Sign in and open the application registration page described in the official docs.",
                "owner": "developer",
                "human_handoff": True,
                "handoff_reason": "Requires the developer to sign in.",
                "prerequisites": [],
                "source_ids": ["S1"],
                "evidence_status": "sourced",
                "troubleshooting_notes": None,
            },
            {
                "order": 2,
                "title": "Create the OAuth application",
                "instructions": "Create an application and set the redirect/callback URL required by your agent.",
                "owner": "developer",
                "human_handoff": True,
                "handoff_reason": "Creating an app and handling secrets must be done by the developer.",
                "prerequisites": ["Developer account"],
                "source_ids": ["S1"],
                "evidence_status": "sourced",
                "troubleshooting_notes": "If redirect URL validation fails, compare the exact URI with the docs.",
            },
        ],
        "blockers": [],
        "sources": [],
        "testing_record": {
            "tested": False,
            "attempts": [],
            "notes": "No authenticated setup was performed.",
        },
        "unknowns": ["Provider approval wait is unknown."],
        "next_action": {
            "title": "Create the OAuth app",
            "description": "Sign in to the official developer portal and register the application.",
            "owner": "developer",
        },
        "evidence_quality": {
            "rating": "moderate",
            "summary": "Official documentation snippets describe registration, but this agent did not complete setup.",
        },
    }


class FakeMistral:
    def __init__(self, responses: list[dict | Exception]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def complete_json(self, *, system: str, user: str) -> dict:
        self.calls.append({"system": system, "user": user})
        if not self.responses:
            raise UpstreamServiceError("No mocked Mistral response remaining.")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeTavily:
    def __init__(self, results: list[Source] | Exception) -> None:
        self.results = results
        self.queries: list[str] = []

    def search(self, query: str, *, candidate_domain: str | None = None) -> list[Source]:
        self.queries.append(query)
        if isinstance(self.results, Exception):
            raise self.results
        return list(self.results)
