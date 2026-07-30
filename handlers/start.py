from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
)

import config

router = Router()

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Доход"), KeyboardButton(text="➖ Расход")],
        [KeyboardButton(text="🔄 Обмен нал→карта")],
        [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="📜 История"), KeyboardButton(text="🤝 Долги")],
    ],
    resize_keyboard=True,
)


def _cabinet_inline_keyboard():
    """Инлайн-кнопка кабинета. В отличие от кнопки в reply-клавиатуре,
    у инлайн-кнопки Telegram передаёт initData — иначе сайт не сможет
    узнать, кто его открыл. Показываем её только если WEBAPP_URL настроен."""
    if not config.WEBAPP_URL.startswith("https://"):
        return None
    url = config.WEBAPP_URL.rstrip("/") + "/app"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧮 Открыть кабинет", web_app=WebAppInfo(url=url))]
    ])


@router.message(CommandStart())
async def cmd_start(message: Message):
    from database import db
    await db.upsert_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )
    await message.answer(
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        "Я — твоя бухгалтерия. Считаю доходы, расходы и комиссии за переводы, "
        "и помогу не забывать записывать траты.\n\n"
        "Всё, что добавишь тут или в личном кабинете на сайте — "
        "сразу видно в обоих местах, это одна база.\n\n"
        "Выбери действие:",
        reply_markup=MAIN_KEYBOARD,
    )

    kb = _cabinet_inline_keyboard()
    if kb:
        await message.answer(
            "Кабинет также всегда доступен по кнопке рядом с полем ввода (☰ / 🧮).",
            reply_markup=kb,
        )
