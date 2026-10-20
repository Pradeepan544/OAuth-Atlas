from __future__ import annotations

from threading import Lock

from app.schemas import OAuthGuide
from app.storage.database import connect


class GuideRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self._lock = Lock()
        self._connection = connect(database_path)

    def save(self, guide: OAuthGuide) -> None:
        payload = guide.model_dump_json()
        with self._lock:
            self._connection.execute(
                "INSERT OR REPLACE INTO guides (id, created_at, payload) VALUES (?, ?, ?)",
                (guide.id, guide.generated_at.isoformat(), payload),
            )
            self._connection.commit()

    def get(self, guide_id: str) -> OAuthGuide | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT payload FROM guides WHERE id = ?",
                (guide_id,),
            ).fetchone()
        if row is None:
            return None
        return OAuthGuide.model_validate_json(row["payload"])

    def close(self) -> None:
        self._connection.close()
