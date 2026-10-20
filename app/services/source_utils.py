from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from app.schemas import Source, SourceType


def hostname_from_url(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.hostname or "").lower()


def registrable_domain(host: str) -> str:
    cleaned = host.lower().removeprefix("www.")
    parts = [part for part in cleaned.split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return cleaned


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        parsed = urlparse(f"https://{url.strip()}")
    path = parsed.path.rstrip("/") or ""
    normalized = urlunparse(
        (parsed.scheme.lower(), (parsed.netloc or "").lower(), path, "", parsed.query, "")
    )
    return normalized


def classify_source(url: str, candidate_domain: str | None) -> SourceType:
    host = hostname_from_url(url)
    if not host:
        return SourceType.uncertain
    if not candidate_domain:
        return SourceType.uncertain
    candidate = candidate_domain.lower().removeprefix("www.")
    host_clean = host.removeprefix("www.")
    if host_clean == candidate or host_clean.endswith(f".{candidate}"):
        return SourceType.official
    if registrable_domain(host_clean) == registrable_domain(candidate):
        return SourceType.official
    return SourceType.secondary


def deduplicate_sources(sources: list[Source]) -> list[Source]:
    seen: set[str] = set()
    unique: list[Source] = []
    for source in sources:
        key = normalize_url(source.url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(source)
    return unique


def limit_sources(sources: list[Source], *, max_sources: int, max_chars: int) -> list[Source]:
    trimmed: list[Source] = []
    for index, source in enumerate(sources[:max_sources], start=1):
        snippet = (source.evidence_snippet or "")[:max_chars]
        trimmed.append(
            source.model_copy(
                update={
                    "id": f"S{index}",
                    "evidence_snippet": snippet,
                }
            )
        )
    return trimmed
