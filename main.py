import asyncio
import logging
import sys
import os
import threading

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import MenuButtonWebApp, MenuButtonDefault, WebAppInfo

import config
from database import db
from handlers import get_handlers_router
from reminders import reminders_loop
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

    # Кнопка "☰"/"🧮" рядом с полем ввода — открывает кабинет с полноценным initData
    # (в отличие от кнопки в reply-клавиатуре, initData там всегда пустой).
    if config.WEBAPP_URL.startswith("https://"):
        url = config.WEBAPP_URL.rstrip("/") + "/app"
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Кабинет", web_app=WebAppInfo(url=url))
        )
        logging.info("Menu button set to Mini App: %s", url)
    else:
        await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        logging.warning("WEBAPP_URL is not set (or not https) — menu button left default")

    asyncio.create_task(reminders_loop(bot))
    logging.info("Reminders task scheduled")

    logging.info("Bot started")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
