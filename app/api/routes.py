from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.errors import (
    ConfigurationError,
    GuideValidationError,
    InvalidRequestError,
    ResearchIncompleteError,
    UpstreamServiceError,
)
from app.schemas import (
    ErrorResponse,
    GenerateGuideRequest,
    GenerateGuideResponse,
    HealthResponse,
    LibraryGuide,
    OAuthGuide,
)
from app.services.mistral_client import MistralClient
from app.services.research_agent import ResearchAgent
from app.services.tavily_search import TavilyClient
from app.storage.library import load_library
from app.storage.repository import GuideRepository

router = APIRouter()

_repository: GuideRepository | None = None
_mistral: MistralClient | None = None
_tavily: TavilyClient | None = None


def get_repository(settings: Settings = Depends(get_settings)) -> GuideRepository:
    global _repository
    if _repository is None or _repository.database_path != settings.database_path:
        _repository = GuideRepository(settings.database_path)
    return _repository


def get_agent(
    settings: Settings = Depends(get_settings),
    repository: GuideRepository = Depends(get_repository),
) -> ResearchAgent:
    global _mistral, _tavily
    if _mistral is None:
        _mistral = MistralClient(settings)
    if _tavily is None:
        _tavily = TavilyClient(settings)
    return ResearchAgent(settings, _mistral, _tavily, repository)


@router.get("/")
def root() -> dict[str, str]:
    return {
        "name": "OAuth Launchpad",
        "status": "ok",
        "health": "/health",
        "docs": "/docs",
        "library": "/api/library",
        "generate": "POST /api/guides/generate",
    }


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/api/library", response_model=list[LibraryGuide])
def library(settings: Settings = Depends(get_settings)) -> list[LibraryGuide]:
    return load_library(settings.seed_guides_path)


@router.post(
    "/api/guides/generate",
    response_model=GenerateGuideResponse,
    responses={
        400: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def generate_guide(
    request: GenerateGuideRequest,
    agent: ResearchAgent = Depends(get_agent),
) -> GenerateGuideResponse:
    try:
        return agent.generate(request)
    except InvalidRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except ResearchIncompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": "incomplete_research", "message": exc.message, "details": exc.details},
        ) from exc
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "configuration_error", "message": exc.message, "details": exc.details},
        ) from exc
    except GuideValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "invalid_model_output", "message": exc.message, "details": exc.details},
        ) from exc
    except UpstreamServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "upstream_error", "message": exc.message, "details": exc.details},
        ) from exc


@router.get(
    "/api/guides/{guide_id}",
    response_model=OAuthGuide,
    responses={404: {"model": ErrorResponse}},
)
def get_guide(guide_id: str, repository: GuideRepository = Depends(get_repository)) -> OAuthGuide:
    guide = repository.get(guide_id)
    if guide is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "No generated guide exists for that ID."},
        )
    return guide
