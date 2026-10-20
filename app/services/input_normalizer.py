from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.errors import InvalidRequestError

_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
_HOST_LIKE_RE = re.compile(
    r"^(?:www\.)?[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)


@dataclass(frozen=True)
class NormalizedInput:
    raw: str
    display_name: str
    hostname: str | None
    input_kind: str


def _is_disallowed_host(host: str) -> bool:
    lowered = host.lower().strip("[]")
    if lowered in {"localhost", "localhost.localdomain"}:
        return True
    try:
        ip = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def extract_hostname(value: str) -> str | None:
    text = value.strip()
    if not text:
        return None
    if " " in text and not _SCHEME_RE.match(text):
        return None
    candidate = text if _SCHEME_RE.match(text) else f"https://{text}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.username or parsed.password:
        raise InvalidRequestError("URLs with embedded credentials are not allowed")
    host = parsed.hostname
    if not host:
        return None
    if _is_disallowed_host(host):
        raise InvalidRequestError(
            "Private, loopback, link-local, and reserved hosts cannot be used as the application identity"
        )
    return host.lower()


def normalize_app_input(raw: str) -> NormalizedInput:
    text = raw.strip()
    if len(text) < 2:
        raise InvalidRequestError("Provide an application name or website with at least 2 characters")
    if text.count("http") > 2:
        raise InvalidRequestError("The application input looks malformed")

    hostname = None
    host_like = text.split("/")[0].split("?")[0].strip().lower().removeprefix("www.")
    looks_like_host = bool(_SCHEME_RE.match(text) or _HOST_LIKE_RE.match(host_like))
    if looks_like_host:
        hostname = extract_hostname(text)

    if hostname:
        display = hostname.removeprefix("www.")
        return NormalizedInput(raw=text, display_name=display, hostname=hostname, input_kind="url")

    return NormalizedInput(raw=text, display_name=text, hostname=None, input_kind="name")
