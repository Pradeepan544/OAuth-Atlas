import logging
import time

import httpx

logger = logging.getLogger("app.http")

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def request_with_retries(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    max_attempts: int = 3,
    retryable_status: set[int] | None = None,
    **kwargs,
) -> httpx.Response:
    """Send an HTTP request with a small number of retries for transient failures."""
    attempts = max(1, max_attempts)
    retry_on = retryable_status or RETRYABLE_STATUS
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = client.request(method, url, **kwargs)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
            logger.warning("HTTP %s failed on attempt %s/%s: %s", method, attempt, attempts, exc.__class__.__name__)
            if attempt == attempts:
                raise
            time.sleep(0.4 * attempt)
            continue

        if response.status_code in retry_on and attempt < attempts:
            logger.warning(
                "HTTP %s returned %s on attempt %s/%s",
                method,
                response.status_code,
                attempt,
                attempts,
            )
            time.sleep(0.4 * attempt)
            continue
        return response

    if last_error:
        raise last_error
    raise RuntimeError("HTTP retry loop ended without a response")
