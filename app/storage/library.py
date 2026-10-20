from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas import LibraryGuide


@lru_cache
def load_library(seed_path: str) -> list[LibraryGuide]:
    path = Path(seed_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return [LibraryGuide.model_validate(item) for item in data]
