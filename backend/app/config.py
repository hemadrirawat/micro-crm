"""Runtime configuration, read once from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

# The sample dataset ends on 2026-08-31. Scoring is relative to "today", so the demo
# pins today to the morning after the last interaction. Set CRM_TODAY=real to use the
# system clock instead.
DEFAULT_DEMO_TODAY = "2026-09-01"


@dataclass(frozen=True)
class Settings:
    database_path: Path
    today_override: str
    llm_api_key: str | None
    llm_base_url: str
    llm_model: str
    llm_timeout_seconds: float
    cors_origins: tuple[str, ...]

    def today(self) -> date:
        if self.today_override.lower() == "real":
            return date.today()
        return date.fromisoformat(self.today_override)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key)


def load_settings() -> Settings:
    return Settings(
        database_path=Path(os.getenv("CRM_DB_PATH", BACKEND_DIR / "data" / "crm.db")),
        today_override=os.getenv("CRM_TODAY", DEFAULT_DEMO_TODAY),
        llm_api_key=os.getenv("LLM_API_KEY") or None,
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        llm_timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
        cors_origins=tuple(
            o.strip()
            for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
            if o.strip()
        ),
    )
