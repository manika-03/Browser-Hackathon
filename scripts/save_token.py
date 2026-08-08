from __future__ import annotations

from getpass import getpass
from pathlib import Path


def main() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    token = getpass("Paste the new Telegram token (input hidden): ").strip()
    if ":" not in token or len(token) < 30:
        raise SystemExit("That does not look like a Telegram bot token. Nothing was saved.")

    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            updated.append(f"TELEGRAM_BOT_TOKEN={token}")
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.insert(0, f"TELEGRAM_BOT_TOKEN={token}")

    env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print(f"Token saved securely to {env_path}")


if __name__ == "__main__":
    main()
