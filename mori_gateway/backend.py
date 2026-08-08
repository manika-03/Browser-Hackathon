from __future__ import annotations

from typing import Any, Protocol

import httpx

from .models import Action, Result


class BackendError(RuntimeError):
    pass


class Backend(Protocol):
    async def respond(self, event: dict[str, Any]) -> Result: ...
    async def close(self) -> None: ...


class HttpBackend:
    def __init__(self, url: str, timeout: float, api_key: str | None) -> None:
        headers = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self.url = url
        self.client = httpx.AsyncClient(timeout=timeout, headers=headers)

    async def respond(self, event: dict[str, Any]) -> Result:
        try:
            response = await self.client.post(self.url, json=event)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Response must be a JSON object")
            return Result.parse(data)
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise BackendError(str(exc)) from exc

    async def close(self) -> None:
        await self.client.aclose()


class MockBackend:
    async def respond(self, payload: dict[str, Any]) -> Result:
        event = payload.get("event", {})
        if event.get("type") == "command" and event.get("command") == "reset":
            return Result("Fresh start. What do you want to learn or find next?")
        if event.get("type") == "action":
            return self._action(str(event.get("action_id", "")))

        text = str(event.get("text", "")).lower()
        if any(word in text for word in ("ml engineer", "machine learning", "ai automation")):
            return Result(
                "I can build that route. What is your current level, and how many hours can you study each week?",
                (Action("profile:beginner", "Beginner"), Action("profile:intermediate", "Intermediate")),
            )
        if "hackathon" in text:
            return Result(
                "Which city or region should I search, and are online events acceptable?",
                (Action("location:delhi", "Delhi-NCR"), Action("location:online", "Online is fine")),
            )
        if "forms.gle" in text or "docs.google.com/forms" in text:
            return Result(
                "I found the form link. The connected browser backend will inspect it, ask for missing answers, and stop before submission.",
                (Action("form:inspect", "Inspect form"),),
            )
        return Result(
            "Tell me your current level, location, weekly study time, and whether you prefer mostly free options.",
            (Action("goal:free", "Mostly free"), Action("goal:credential", "Best credential")),
        )

    def _action(self, action_id: str) -> Result:
        messages = {
            "starter:learning": "What do you want to learn or become?",
            "starter:hackathons": "Which city should I search, and are online events acceptable?",
            "starter:form": "Send the Google Form link. I will inspect it before asking for answers.",
            "profile:beginner": "Beginner selected. How many hours can you study each week, and what is your budget?",
            "profile:intermediate": "Intermediate selected. What have you already built, and what timeline are you targeting?",
            "location:delhi": "Delhi-NCR selected. The connected backend will check current event pages and deadlines.",
            "location:online": "I will include nearby and online events, clearly labelled by mode.",
            "goal:free": "I will prioritize free resources and include paid options only when their value is clear.",
            "goal:credential": "I will prioritize recognized credentials without implying job guarantees.",
            "form:inspect": "Connect MORI_BACKEND_URL to enable live browser form inspection.",
        }
        return Result(messages.get(action_id, "That action expired. Please send the request again."))

    async def close(self) -> None:
        return None

