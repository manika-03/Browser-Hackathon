# MORI Telegram Gateway

Telegram bot: https://t.me/MoriPathBot

This service owns MORI's Telegram conversation layer and forwards normalized events to the partner backend. If `MORI_BACKEND_URL` is blank, it uses a stateful local demo backend with complete learning-roadmap and opportunity flows.

For partner integration and safe GitHub sharing, start with [HANDOFF.md](HANDOFF.md). Commit `.env.example`, but never commit `.env` or any real secret value.

## Run

```powershell
.\.venv\Scripts\python.exe -m mori_gateway
```

In Telegram, send `/demo` for the guaranteed end-to-end ML roadmap and `/webcmd` to verify the local Webcmd integration.

## Connect the backend

Set the partner's complete endpoint in `.env`:

```text
MORI_BACKEND_URL=http://127.0.0.1:8000/v1/mori/respond
```

See [the backend contract](docs/backend-contract.md). Never commit `.env` or share the Telegram token.

## Profile picture

In `@BotFather`, send `/setuserpic`, select `@MoriPathBot`, and upload [the MORI artwork](assets/mori-profile.png).
