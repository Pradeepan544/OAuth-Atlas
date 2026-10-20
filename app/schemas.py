from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Difficulty(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"
    unknown = "unknown"


class OAuthType(str, Enum):
    oauth2 = "oauth2"
    oauth1 = "oauth1"
    oidc = "oidc"
    mixed = "mixed"
    unknown = "unknown"


class EvidenceStatus(str, Enum):
    sourced = "sourced"
    inferred = "inferred"
    unknown = "unknown"


class SourceType(str, Enum):
    official = "official"
    secondary = "secondary"
    uncertain = "uncertain"


class StepOwner(str, Enum):
    developer = "developer"
    agent = "agent"
    mixed = "mixed"
    provider = "provider"


class ApprovalWaitStatus(str, Enum):
    unknown = "unknown"
    documented = "documented"
    provider_dependent = "provider_dependent"
    none_indicated = "none_indicated"


class EstimateKind(str, Enum):
    estimate = "estimate"
    documented = "documented"
    unknown = "unknown"


class GenerateGuideRequest(BaseModel):
    app_name_or_url: str = Field(..., min_length=1, max_length=200)
    integration_goal: Optional[str] = Field(default=None, max_length=500)
    requested_scopes: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("app_name_or_url")
    @classmethod
    def strip_app_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("app_name_or_url cannot be empty")
        return cleaned

    @field_validator("integration_goal")
    @classmethod
    def strip_goal(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("requested_scopes")
    @classmethod
    def clean_scopes(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            text = item.strip()
            if not text:
                continue
            if len(text) > 120:
                raise ValueError("requested_scopes items must be 120 characters or fewer")
            cleaned.append(text)
        return cleaned


class SourceLink(BaseModel):
    title: str
    url: str


class LibraryGuide(BaseModel):
    id: str
    app_name: str
    official_domain: str
    difficulty: Difficulty
    description: str
    source_links: list[SourceLink]
    review_status: str
    notes: str


class ApprovalWait(BaseModel):
    status: ApprovalWaitStatus = ApprovalWaitStatus.unknown
    documented_range: Optional[str] = None
    notes: str = "No verified approval wait was recorded."


class TimeEstimate(BaseModel):
    hands_on_minutes_min: Optional[int] = Field(default=None, ge=0, le=10080)
    hands_on_minutes_max: Optional[int] = Field(default=None, ge=0, le=10080)
    kind: EstimateKind = EstimateKind.estimate
    confidence: Literal["low", "medium", "high", "unknown"] = "unknown"
    rationale: str
    approval_wait: ApprovalWait = Field(default_factory=ApprovalWait)


class Prerequisite(BaseModel):
    item: str
    required: bool = True
    notes: Optional[str] = None
    source_ids: list[str] = Field(default_factory=list)
    evidence_status: EvidenceStatus = EvidenceStatus.unknown


class GuideStep(BaseModel):
    order: int = Field(..., ge=1, le=20)
    title: str = Field(..., min_length=1, max_length=160)
    instructions: str = Field(..., min_length=1, max_length=4000)
    owner: StepOwner
    human_handoff: bool
    handoff_reason: Optional[str] = None
    prerequisites: list[str] = Field(default_factory=list, max_length=10)
    source_ids: list[str] = Field(default_factory=list, max_length=12)
    evidence_status: EvidenceStatus = EvidenceStatus.unknown
    troubleshooting_notes: Optional[str] = Field(default=None, max_length=2000)


class Source(BaseModel):
    id: str
    title: str
    url: str
    domain: str
    source_type: SourceType
    evidence_snippet: str = ""
    relevance: Optional[float] = None


class TestAttempt(BaseModel):
    action: str
    outcome: str
    timestamp: Optional[datetime] = None


class TestingRecord(BaseModel):
    tested: bool = False
    attempts: list[TestAttempt] = Field(default_factory=list)
    notes: str = "This backend did not sign in to the provider or complete an authenticated OAuth setup."


class Blocker(BaseModel):
    title: str
    description: str
    evidence_status: EvidenceStatus = EvidenceStatus.unknown
    source_ids: list[str] = Field(default_factory=list)


class NextAction(BaseModel):
    title: str
    description: str
    owner: StepOwner = StepOwner.developer


class ResearchAction(BaseModel):
    stage: str
    action: str
    detail: str
    query: Optional[str] = None
    result_count: Optional[int] = None
    status: str = "ok"


class ResearchActivity(BaseModel):
    actions: list[ResearchAction] = Field(default_factory=list)
    search_rounds: int = 0
    repair_attempts: int = 0
    mistral_calls: int = 0
    tavily_calls: int = 0


class EvidenceQuality(BaseModel):
    rating: Literal["strong", "moderate", "weak", "insufficient"] = "weak"
    summary: str


class OAuthGuide(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    app_name: str
    submitted_input: str
    official_domain: Optional[str] = None
    oauth_type: OAuthType = OAuthType.unknown
    integration_goal: Optional[str] = None
    summary: str
    difficulty: Difficulty = Difficulty.unknown
    difficulty_reason: str
    time_estimate: TimeEstimate
    prerequisites: list[Prerequisite] = Field(default_factory=list, max_length=15)
    steps: list[GuideStep] = Field(..., min_length=1, max_length=15)
    blockers: list[Blocker] = Field(default_factory=list, max_length=10)
    sources: list[Source] = Field(default_factory=list, max_length=20)
    testing_record: TestingRecord = Field(default_factory=TestingRecord)
    unknowns: list[str] = Field(default_factory=list, max_length=20)
    next_action: NextAction
    research_activity: ResearchActivity = Field(default_factory=ResearchActivity)
    generated_at: datetime
    evidence_quality: EvidenceQuality


class GuideDraft(BaseModel):
    """Model-produced fields before persistence metadata is attached."""

    model_config = ConfigDict(extra="ignore")

    app_name: str
    official_domain: Optional[str] = None
    oauth_type: OAuthType = OAuthType.unknown
    summary: str
    difficulty: Difficulty = Difficulty.unknown
    difficulty_reason: str
    time_estimate: TimeEstimate
    prerequisites: list[Prerequisite] = Field(default_factory=list, max_length=15)
    steps: list[GuideStep] = Field(..., min_length=1, max_length=15)
    blockers: list[Blocker] = Field(default_factory=list, max_length=10)
    sources: list[Source] = Field(default_factory=list, max_length=20)
    testing_record: TestingRecord = Field(default_factory=TestingRecord)
    unknowns: list[str] = Field(default_factory=list, max_length=20)
    next_action: NextAction
    evidence_quality: EvidenceQuality


class ResearchPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")

    likely_app_name: str
    candidate_official_domain: Optional[str] = None
    identity_confidence: Literal["low", "medium", "high"]
    identity_rationale: str
    search_queries: list[str] = Field(..., min_length=1, max_length=5)
    research_objectives: list[str] = Field(..., min_length=1, max_length=8)
    uncertainties: list[str] = Field(default_factory=list, max_length=8)
    clarification_needed: bool = False
    clarification_question: Optional[str] = None

    @field_validator("search_queries")
    @classmethod
    def limit_query_length(cls, value: list[str]) -> list[str]:
        cleaned = []
        for query in value:
            text = " ".join(query.strip().split())
            if not text:
                continue
            cleaned.append(text[:220])
        if not cleaned:
            raise ValueError("at least one search query is required")
        return cleaned[:5]


class ExtraSearch(BaseModel):
    query: str = Field(..., min_length=3, max_length=220)
    reason: str = Field(..., min_length=3, max_length=400)


class EvidenceReview(BaseModel):
    model_config = ConfigDict(extra="ignore")

    unanswered_questions: list[str] = Field(default_factory=list, max_length=10)
    additional_searches: list[ExtraSearch] = Field(default_factory=list)
    sufficient_to_identify_app: bool
    notes: str

    @field_validator("additional_searches")
    @classmethod
    def cap_additional_searches(cls, value: list[ExtraSearch]) -> list[ExtraSearch]:
        return value[:2]


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict = Field(default_factory=dict)


class GenerateGuideResponse(BaseModel):
    status: Literal["complete", "incomplete", "failed"]
    message: str
    guide: Optional[OAuthGuide] = None
    research_activity: ResearchActivity = Field(default_factory=ResearchActivity)


class HealthResponse(BaseModel):
    status: Literal["ok"]
