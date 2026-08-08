from __future__ import annotations

import asyncio
import re
import shutil
from dataclasses import dataclass
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


@dataclass
class Session:
    goal: str = "machine learning engineer"
    level: str = "beginner"
    location: str = "Delhi-NCR"
    hours: int = 10
    preference: str = "mostly free"
    awaiting_profile: bool = False


class LocalDemoBackend:
    """Stateful, deterministic fallback used until the partner API is connected."""

    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}

    async def respond(self, payload: dict[str, Any]) -> Result:
        event = payload.get("event", {})
        session_id = str(payload.get("session_id", "demo"))
        session = self.sessions.setdefault(session_id, Session())

        if event.get("type") == "command":
            command = str(event.get("command", ""))
            if command == "reset":
                self.sessions[session_id] = Session()
                return Result("Fresh start. Tell me what you want to learn or find.")
            if command == "demo":
                return self._roadmap(session)
            if command == "webcmd":
                return await self._webcmd_status()

        if event.get("type") == "action":
            return self._action(session, str(event.get("action_id", "")))

        raw_text = str(event.get("text", "")).strip()
        text = raw_text.lower()
        self._read_profile(session, text)

        if "forms.gle" in text or "docs.google.com/forms" in text:
            return Result(
                "I found the Google Form. MORI's browser layer can inspect its fields and prepare answers, but it will always pause before submission.",
                (Action("form:inspect", "Inspect safely"),),
            )
        if "salary" in text or "earn" in text or "package" in text:
            return self._salary_answer(session)
        if "hackathon" in text or "competition" in text:
            return self._hackathons(session)

        learning_terms = ("learn", "become", "engineer", "course", "certification", "ai automation", "machine learning")
        if any(term in text for term in learning_terms):
            session.goal = self._goal_from(text)
            if self._has_profile_details(text):
                session.awaiting_profile = False
                return self._roadmap(session)
            session.awaiting_profile = True
            return Result(
                f"Great goal: {session.goal.title()}. Send your level, location, weekly study time, and budget in one message.\n\nExample: Beginner, Delhi, 10 hours/week, mostly free.",
                (Action("profile:beginner", "Beginner"), Action("profile:intermediate", "Intermediate")),
            )

        # Any reply after MORI asks for a profile should complete the route instead of looping.
        if session.awaiting_profile:
            session.awaiting_profile = False
            return self._roadmap(session)

        if text in {"yes", "yes please", "go", "continue", "show me", "mostly free"}:
            return self._roadmap(session)

        return Result(
            "Tell me a goal and I will turn it into an actionable route.\n\nTry: I want to become an ML engineer. Beginner, Delhi, 10 hours/week, mostly free.",
            (Action("demo:ml", "Run ML demo"), Action("starter:hackathons", "Find hackathons")),
        )

    def _action(self, session: Session, action_id: str) -> Result:
        if action_id in {"demo:ml", "goal:free", "goal:credential"}:
            session.preference = "best credential" if action_id == "goal:credential" else "mostly free"
            session.awaiting_profile = False
            return self._roadmap(session)
        if action_id == "starter:learning":
            session.awaiting_profile = True
            return Result("What do you want to learn or become? Include your level, location, hours per week, and budget if you know them.")
        if action_id in {"starter:hackathons", "location:delhi", "location:online"}:
            if action_id == "location:online":
                session.location = "online"
            return self._hackathons(session)
        if action_id == "starter:form":
            return Result("Send the public Google Form link. MORI will inspect it and pause before any submission.")
        if action_id == "profile:beginner":
            session.level = "beginner"
            session.awaiting_profile = True
            return Result("Beginner selected. Send your location, weekly hours, and budget in one message. Example: Delhi, 10 hours, mostly free.")
        if action_id == "profile:intermediate":
            session.level = "intermediate"
            session.awaiting_profile = True
            return Result("Intermediate selected. Send your location, weekly hours, and budget in one message.")
        if action_id == "form:inspect":
            return Result("Form inspection is approval-first. Connect the browser backend for live field extraction; MORI will never submit without confirmation.")
        return Result("That action expired. Send your request again or use /demo.")

    @staticmethod
    def _read_profile(session: Session, text: str) -> None:
        if "intermediate" in text:
            session.level = "intermediate"
        elif "beginner" in text or "starting" in text:
            session.level = "beginner"
        if "delhi" in text or "noida" in text or "gurgaon" in text or "gurugram" in text:
            session.location = "Delhi-NCR"
        if "online" in text:
            session.location = "online"
        match = re.search(r"\b(\d{1,2})\s*(?:hours?|hrs?)", text)
        if match:
            session.hours = max(1, min(40, int(match.group(1))))
        if "free" in text or "no budget" in text:
            session.preference = "mostly free"
        elif "paid" in text or "credential" in text:
            session.preference = "best credential"

    @staticmethod
    def _has_profile_details(text: str) -> bool:
        return bool(re.search(r"\b\d{1,2}\s*(?:hours?|hrs?)", text)) or "beginner" in text or "intermediate" in text

    @staticmethod
    def _goal_from(text: str) -> str:
        if "automation" in text:
            return "AI automation specialist"
        if "data scientist" in text:
            return "data scientist"
        if "web develop" in text:
            return "web developer"
        return "machine learning engineer"

    @staticmethod
    def _roadmap(session: Session) -> Result:
        return Result(
            f"MORI ROADMAP: {session.goal.upper()}\n"
            f"Profile: {session.level.title()} | {session.location} | {session.hours} hrs/week | {session.preference}\n\n"
            "1. FOUNDATION (Weeks 1-2)\n"
            "Python + data basics with Kaggle Learn:\nhttps://www.kaggle.com/learn/python\n\n"
            "2. CORE ML (Weeks 3-6)\n"
            "Google Machine Learning Crash Course, free and practical:\nhttps://developers.google.com/machine-learning/crash-course\n\n"
            "3. BUILD (Weeks 7-9)\n"
            "Kaggle Intro to ML, then publish one end-to-end project:\nhttps://www.kaggle.com/learn/intro-to-machine-learning\n\n"
            "4. DEEPEN (Weeks 10-12)\n"
            "fast.ai Practical Deep Learning, free:\nhttps://course.fast.ai/\n\n"
            "5. OPTIONAL PAID CREDENTIAL\n"
            "Andrew Ng's Machine Learning Specialization. Choose it for structure and a recognized certificate, not as a job guarantee:\nhttps://www.coursera.org/specializations/machine-learning-introduction\n\n"
            "6. OPPORTUNITIES\n"
            "Track current hackathons on Devfolio and Unstop:\nhttps://devfolio.co/hackathons\nhttps://unstop.com/hackathons\n\n"
            f"Weekly plan: {max(2, session.hours // 2)} hrs concepts, {max(2, session.hours // 3)} hrs practice, and the rest on one portfolio project.\n\n"
            "Why these picks: free-first, project-led, beginner-safe, and based on primary course pages. MORI uses Webcmd as its live-web execution layer; this local demo keeps vetted fallback sources so the route still completes if a website is unavailable.",
            (
                Action("goal:credential", "Prioritize credential"),
                Action("starter:hackathons", "Find hackathons"),
            ),
        )

    @staticmethod
    def _hackathons(session: Session) -> Result:
        return Result(
            f"HACKATHON WATCHLIST: {session.location}\n\n"
            "I would verify dates, mode, eligibility, and the official registration deadline before ranking any event. Start with these live discovery pages:\n\n"
            "Devfolio: https://devfolio.co/hackathons\n"
            "Unstop: https://unstop.com/hackathons\n"
            "MLH events: https://mlh.io/seasons/2026/events\n"
            "HackerEarth challenges: https://www.hackerearth.com/challenges/hackathon/\n"
            "Luma Delhi discovery: https://lu.ma/delhi\n\n"
            "MORI's Webcmd workflow opens these sources, extracts comparable fields, removes expired events, and returns to the browser when a page changes.",
            (Action("demo:ml", "Build learning route"),),
        )

    @staticmethod
    def _salary_answer(session: Session) -> Result:
        return Result(
            f"For a {session.goal} role, salary depends heavily on city, experience, company type, and demonstrable projects. MORI should compare current role pages from Glassdoor, AmbitionBox, Levels.fyi, and live job listings before quoting a range.\n\n"
            "Focus on the evidence employers can verify: Python, ML fundamentals, deployment, one strong end-to-end project, and clear communication. I would label every salary estimate with source date and location rather than present it as a guarantee."
        )

    @staticmethod
    async def _webcmd_status() -> Result:
        executable = shutil.which("webcmd")
        if not executable:
            return Result("Webcmd is not installed on this machine. MORI is using its vetted local fallback catalog.")
        try:
            process = await asyncio.create_subprocess_exec(
                executable,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=5)
            version = stdout.decode(errors="replace").strip()
        except (OSError, TimeoutError):
            return Result("Webcmd is installed but did not respond. MORI is using its vetted local fallback catalog.")
        return Result(
            f"Webcmd {version} is connected. In MORI, Webcmd handles live website exploration, structured extraction, reusable browser commands, and recovery when a site changes."
        )

    async def close(self) -> None:
        return None


# Backwards-compatible name for existing partner imports.
MockBackend = LocalDemoBackend
