from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

router = Router()

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Доход"), KeyboardButton(text="➖ Расход")],
        [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="📜 История"), KeyboardButton(text="🤝 Долги")],
    ],
    resize_keyboard=True,
)


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
        "Я помогу тебе отслеживать финансы.\n"
        "Выбери действие:",
        reply_markup=MAIN_KEYBOARD,
    )
