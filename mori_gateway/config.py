from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _chat_ids(raw: str) -> frozenset[int]:
    return frozenset(int(value.strip()) for value in raw.split(",") if value.strip())


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    backend_url: str | None
    backend_api_key: str | None
    backend_timeout: float
    allowed_chat_ids: frozenset[int]
    log_level: str

    @classmethod
    def from_environment(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is missing from the local environment")

        backend_url = os.getenv("MORI_BACKEND_URL", "").strip() or None
        if backend_url and not backend_url.startswith(("http://", "https://")):
            raise RuntimeError("MORI_BACKEND_URL must start with http:// or https://")

        return cls(
            telegram_bot_token=token,
            backend_url=backend_url,
            backend_api_key=os.getenv("MORI_BACKEND_API_KEY", "").strip() or None,
            backend_timeout=float(os.getenv("MORI_BACKEND_TIMEOUT_SECONDS", "60")),
            allowed_chat_ids=_chat_ids(os.getenv("MORI_ALLOWED_CHAT_IDS", "")),
            log_level=os.getenv("MORI_LOG_LEVEL", "INFO").upper(),
        )

    def allows(self, chat_id: int) -> bool:
        return not self.allowed_chat_ids or chat_id in self.allowed_chat_ids

