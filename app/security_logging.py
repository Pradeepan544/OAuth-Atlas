import logging
from typing import Iterable


REDACTED = "[REDACTED]"


def redact_text(text: str, secrets: Iterable[str]) -> str:
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, REDACTED)
    return redacted


class SecretRedactFilter(logging.Filter):
    def __init__(self, secrets: Iterable[str]) -> None:
        super().__init__()
        self._secrets = [secret for secret in secrets if secret]

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = redact_text(message, self._secrets)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def install_secret_filter(secrets: Iterable[str]) -> SecretRedactFilter:
    secret_filter = SecretRedactFilter(secrets)
    logging.getLogger().addFilter(secret_filter)
    for name in ("app", "httpx", "uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).addFilter(secret_filter)
    return secret_filter
