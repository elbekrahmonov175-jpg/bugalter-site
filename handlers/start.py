from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

import config

router = Router()


def _cabinet_button() -> KeyboardButton:
    """Кнопка личного кабинета. WebApp-кнопка работает только с https-адресом,
    поэтому если WEBAPP_URL не задан (например, при локальном запуске),
    показываем обычную кнопку-подсказку вместо неё."""
    if config.WEBAPP_URL.startswith("https://"):
        url = config.WEBAPP_URL.rstrip("/") + "/app"
        return KeyboardButton(text="🧮 Кабинет", web_app=WebAppInfo(url=url))
    return KeyboardButton(text="🧮 Кабинет (сайт не настроен)")


def build_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Доход"), KeyboardButton(text="➖ Расход")],
            [KeyboardButton(text="🔄 Обмен нал→карта")],
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="📜 История"), KeyboardButton(text="🤝 Долги")],
            [_cabinet_button()],
        ],
        resize_keyboard=True,
    )


MAIN_KEYBOARD = build_main_keyboard()


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
