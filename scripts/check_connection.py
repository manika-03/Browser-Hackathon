import asyncio

from telegram import Bot

from mori_gateway.config import Settings


async def main() -> None:
    settings = Settings.from_environment()
    async with Bot(settings.telegram_bot_token) as bot:
        identity = await bot.get_me()
        print(f"verified_username=@{identity.username}")
        print(f"verified_bot_id={identity.id}")


if __name__ == "__main__":
    asyncio.run(main())
