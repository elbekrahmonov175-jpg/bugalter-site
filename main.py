import asyncio
import logging
import sys
import os
import threading

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from database import db
from handlers import get_handlers_router
from web.app import run_web


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is empty! Check Railway Variables!")
        return

    # Запускаем Flask в отдельном потоке
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    logging.info("Web server started")

    await db.init_db()
    logging.info("Database initialized")

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(get_handlers_router())

    logging.info("Bot started")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
