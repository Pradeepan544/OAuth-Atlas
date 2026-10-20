from __future__ import annotations

import json
import logging
import re

import httpx

from app.config import Settings
from app.errors import ConfigurationError, UpstreamServiceError
from app.http_utils import request_with_retries

logger = logging.getLogger("app.mistral")
_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class MistralClient:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=settings.mistral_timeout_seconds)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def complete_json(self, *, system: str, user: str) -> dict:
        if not self.settings.mistral_api_key.strip():
            raise ConfigurationError("MISTRAL_API_KEY is missing. Add it to your .env file.")

        payload = {
            "model": self.settings.mistral_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.settings.mistral_temperature,
            "max_tokens": self.settings.mistral_max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.mistral_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = request_with_retries(
                self._client,
                "POST",
                self.settings.mistral_url,
                max_attempts=self.settings.http_max_attempts,
                headers=headers,
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise UpstreamServiceError(
                "Mistral timed out while generating a response.",
                details={"service": "mistral"},
            ) from exc
        except httpx.HTTPError as exc:
            raise UpstreamServiceError(
                "Mistral could not be reached.",
                details={"service": "mistral"},
            ) from exc

        if response.status_code in {401, 403}:
            raise ConfigurationError("Mistral rejected the API key. Check MISTRAL_API_KEY.")
        if response.status_code >= 400:
            raise UpstreamServiceError(
                "Mistral returned an error.",
                details={"service": "mistral", "status_code": response.status_code},
            )

        try:
            data = response.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})

            content = message.get("content")

            # Log diagnostic details without exposing your API key or response content.
            logger.warning(
                "AI response diagnostics: model=%s, finish_reason=%s, "
                "native_finish_reason=%s, message_keys=%s, content_type=%s, "
                "content_length=%s, response_error=%s",
                data.get("model"),
                choice.get("finish_reason"),
                choice.get("native_finish_reason"),
                list(message.keys()) if isinstance(message, dict) else [],
                type(content).__name__,
                len(content) if isinstance(content, (str, list)) else None,
                data.get("error"),
            )
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            logger.exception("Failed to inspect the AI provider response.")
            raise UpstreamServiceError(
                "The AI provider returned an unexpected response shape."
            ) from exc

        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
        if not isinstance(content, str) or not content.strip():
            raise UpstreamServiceError("Mistral returned an empty message.")

        return parse_json_object(content)


def parse_json_object(text: str) -> dict:
    cleaned = _FENCE_RE.sub("", text.strip())
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise UpstreamServiceError("Mistral did not return valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise UpstreamServiceError("Mistral JSON was not an object.")
    return parsed
