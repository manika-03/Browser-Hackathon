from .models import Action, Result


WELCOME = """Hi, I'm MORI.

Tell me what you want to learn or where you want to go next. I can build a learning route, compare free and paid resources, find certifications and nearby hackathons, and help prepare application forms.

I will always ask before submitting anything."""

HELP = """Try asking:
- I want to become an ML engineer.
- Find AI automation courses for a beginner.
- Find upcoming hackathons in Delhi-NCR.
- Help me review this Google Form.

Commands: /start, /demo, /webcmd, /reset, /about, /privacy"""

ABOUT = """MORI turns learning goals into sourced, realistic routes. Fit matters more than popularity, and paid recommendations need a clear reason."""

PRIVACY = """Do not send passwords, OTPs, payment credentials, recovery codes, CAPTCHA answers, or sensitive identity documents. MORI prepares forms but always asks before submission."""

START = Result(
    WELCOME,
    (
        Action("starter:learning", "Build a learning path"),
        Action("starter:hackathons", "Find hackathons"),
        Action("starter:form", "Review a form"),
    ),
)
