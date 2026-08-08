from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Action:
    id: str
    label: str
    kind: str = "callback"
    url: str | None = None

    @classmethod
    def parse(cls, data: dict[str, Any]) -> "Action":
        action = cls(
            id=str(data.get("id", "")).strip(),
            label=str(data.get("label", "")).strip(),
            kind=str(data.get("kind", "callback")).strip().lower(),
            url=str(data["url"]).strip() if data.get("url") else None,
        )
        if not action.id or not action.label:
            raise ValueError("Action id and label are required")
        if len(action.id.encode("utf-8")) > 48:
            raise ValueError("Action id exceeds 48 UTF-8 bytes")
        if action.kind not in {"callback", "url"}:
            raise ValueError("Action kind must be callback or url")
        if action.kind == "url" and (not action.url or not action.url.startswith("https://")):
            raise ValueError("URL actions require HTTPS")
        return action


@dataclass(frozen=True)
class Result:
    text: str
    actions: tuple[Action, ...] = ()

    @classmethod
    def parse(cls, data: dict[str, Any]) -> "Result":
        text = str(data.get("text", "")).strip()
        if not text:
            raise ValueError("Backend response text is required")
        raw_actions = data.get("actions") or []
        if not isinstance(raw_actions, list):
            raise ValueError("Backend response actions must be a list")
        return cls(text, tuple(Action.parse(item) for item in raw_actions))


def chunks(text: str, limit: int = 4000) -> list[str]:
    remaining = text.strip()
    output: list[str] = []
    while len(remaining) > limit:
        point = remaining.rfind("\n\n", 0, limit + 1)
        if point < limit // 2:
            point = remaining.rfind(" ", 0, limit + 1)
        if point <= 0:
            point = limit
        output.append(remaining[:point].rstrip())
        remaining = remaining[point:].lstrip()
    if remaining:
        output.append(remaining)
    return output

