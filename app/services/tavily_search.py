from __future__ import annotations

import logging

import httpx

from app.config import Settings
from app.errors import ConfigurationError, UpstreamServiceError
from app.http_utils import request_with_retries
from app.schemas import Source
from app.services.source_utils import classify_source, hostname_from_url

logger = logging.getLogger("app.tavily")


class TavilyClient:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=settings.tavily_timeout_seconds)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def search(self, query: str, *, candidate_domain: str | None = None) -> list[Source]:
        if not self.settings.tavily_api_key.strip():
            raise ConfigurationError("TAVILY_API_KEY is missing. Add it to your .env file.")

        payload = {
            "query": query,
            "search_depth": self.settings.tavily_search_depth,
            "max_results": self.settings.tavily_max_results,
            "topic": self.settings.tavily_topic,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.tavily_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = request_with_retries(
                self._client,
                "POST",
                self.settings.tavily_url,
                max_attempts=self.settings.http_max_attempts,
                headers=headers,
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamServiceError(
                "Tavily Search timed out. Try again in a moment.",
                details={"service": "tavily"},
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamServiceError(
                "Tavily Search could not be reached.",
                details={"service": "tavily"},
            ) from exc

        if response.status_code in {401, 403}:
            raise ConfigurationError("Tavily rejected the API key. Check TAVILY_API_KEY.")
        if response.status_code >= 400:
            raise UpstreamServiceError(
                "Tavily Search returned an error.",
                details={"service": "tavily", "status_code": response.status_code},
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise UpstreamServiceError("Tavily Search returned invalid JSON.") from exc

        results = data.get("results") or []
        sources: list[Source] = []
        for item in results:
            url = (item.get("url") or "").strip()
            if not url:
                continue
            title = (item.get("title") or url).strip()
            snippet = (item.get("content") or item.get("snippet") or "").strip()
            relevance = item.get("score")
            try:
                relevance_value = float(relevance) if relevance is not None else None
            except (TypeError, ValueError):
                relevance_value = None
            sources.append(
                Source(
                    id="pending",
                    title=title[:240],
                    url=url,
                    domain=hostname_from_url(url),
                    source_type=classify_source(url, candidate_domain),
                    evidence_snippet=snippet,
                    relevance=relevance_value,
                )
            )
        logger.info("Tavily search completed with %s results", len(sources))
        return sources
