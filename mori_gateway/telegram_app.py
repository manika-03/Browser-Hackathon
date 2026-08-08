from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from .backend import Backend, BackendError, HttpBackend, MockBackend
from .config import Settings
from .models import Action, Result, chunks
from .persona import ABOUT, HELP, PRIVACY, START


LOG = logging.getLogger(__name__)
COMMANDS = (
    BotCommand("start", "Start with MORI"),
    BotCommand("demo", "Show a complete ML roadmap"),
    BotCommand("webcmd", "Check the Webcmd integration"),
    BotCommand("help", "See what MORI can do"),
    BotCommand("reset", "Reset this conversation"),
    BotCommand("about", "About MORI"),
    BotCommand("privacy", "Privacy and approval rules"),
)


class RedactingFormatter(logging.Formatter):
    def __init__(self, secret: str) -> None:
        super().__init__("%(asctime)s %(levelname)s %(name)s: %(message)s")
        self.secret = secret

    def format(self, record: logging.LogRecord) -> str:
        return super().format(record).replace(self.secret, "[REDACTED]")


def configure_logging(settings: Settings) -> None:
    logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
    formatter = RedactingFormatter(settings.telegram_bot_token)
    for handler in logging.getLogger().handlers:
        handler.setFormatter(formatter)

    # HTTPX logs full Telegram request URLs, which contain the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def _buttons(actions: tuple[Action, ...]) -> InlineKeyboardMarkup | None:
    buttons: list[InlineKeyboardButton] = []
    for action in actions:
        if action.kind == "url":
            buttons.append(InlineKeyboardButton(action.label, url=action.url))
        else:
            data = f"mori:{action.id}"
            if len(data.encode("utf-8")) > 64:
                raise ValueError("Telegram callback data is too long")
            buttons.append(InlineKeyboardButton(action.label, callback_data=data))
    return InlineKeyboardMarkup([buttons[i:i + 2] for i in range(0, len(buttons), 2)]) if buttons else None


def _event(update: Update, event_type: str, **values: str) -> dict[str, Any]:
    user, chat, message = update.effective_user, update.effective_chat, update.effective_message
    if user is None or chat is None:
        raise ValueError("Update has no user or chat")
    return {
        "schema_version": "1.0",
        "request_id": str(uuid4()),
        "persona_id": "mori-v1",
        "channel": "telegram",
        "session_id": f"telegram:{chat.id}",
        "occurred_at": datetime.now(UTC).isoformat(),
        "user": {"id": str(user.id), "display_name": user.full_name, "username": user.username, "language_code": user.language_code},
        "conversation": {"chat_id": str(chat.id), "chat_type": chat.type, "message_id": message.message_id if message else None},
        "event": {"type": event_type, **values},
    }


async def _send(update: Update, result: Result) -> None:
    message = update.effective_message
    if message is None:
        return
    parts = chunks(result.text)
    for index, part in enumerate(parts):
        await message.reply_text(part, reply_markup=_buttons(result.actions) if index == len(parts) - 1 else None, disable_web_page_preview=True)


async def _allowed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    settings: Settings = context.application.bot_data["settings"]
    chat = update.effective_chat
    if chat and settings.allows(chat.id):
        return True
    if update.effective_message:
        await update.effective_message.reply_text("MORI is currently limited to the hackathon demo team.")
    return False


async def _forward(update: Update, context: ContextTypes.DEFAULT_TYPE, event: dict[str, Any]) -> None:
    if update.effective_chat:
        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)
    backend: Backend = context.application.bot_data["backend"]
    try:
        result = await backend.respond(event)
    except BackendError:
        LOG.exception("Backend request failed")
        result = Result("I could not reach the research service. Your request was not repeated automatically, so it is safe to try again.")
    await _send(update, result)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await _allowed(update, context):
        return
    if context.args and context.args[0].lower() == "demo":
        await _forward(update, context, _event(update, "command", command="demo"))
        return
    await _send(update, START)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _allowed(update, context): await _send(update, Result(HELP))


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _allowed(update, context): await _send(update, Result(ABOUT))


async def privacy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _allowed(update, context): await _send(update, Result(PRIVACY))


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _allowed(update, context): await _forward(update, context, _event(update, "command", command="reset"))


async def demo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _allowed(update, context): await _forward(update, context, _event(update, "command", command="demo"))


async def webcmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _allowed(update, context): await _forward(update, context, _event(update, "command", command="webcmd"))


async def text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await _allowed(update, context):
        value = update.effective_message.text if update.effective_message else ""
        await _forward(update, context, _event(update, "text", text=value))


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or not await _allowed(update, context): return
    data = query.data or ""
    if not data.startswith("mori:"):
        await query.answer("This action expired.", show_alert=True)
        return
    await query.answer()
    await _forward(update, context, _event(update, "action", action_id=data.removeprefix("mori:")))


async def post_init(app: Application) -> None:
    await app.bot.set_my_name("MORI")
    await app.bot.set_my_short_description("Learning paths, trusted resources, hackathons, and careful application help.")
    await app.bot.set_my_description("MORI turns goals into sourced learning routes with courses, certifications, videos, hackathons, and approval-first form help.")
    await app.bot.set_my_commands(COMMANDS)
    identity = await app.bot.get_me()
    LOG.info("Connected as @%s", identity.username)


async def post_shutdown(app: Application) -> None:
    await app.bot_data["backend"].close()


def build(settings: Settings) -> Application:
    app = ApplicationBuilder().token(settings.telegram_bot_token).post_init(post_init).post_shutdown(post_shutdown).build()
    app.bot_data["settings"] = settings
    app.bot_data["backend"] = HttpBackend(settings.backend_url, settings.backend_timeout, settings.backend_api_key) if settings.backend_url else MockBackend()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("demo", demo))
    app.add_handler(CommandHandler("webcmd", webcmd_status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("privacy", privacy))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    return app


def run() -> None:
    settings = Settings.from_environment()
    configure_logging(settings)
    build(settings).run_polling(allowed_updates=Update.ALL_TYPES)
