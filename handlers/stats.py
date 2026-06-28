from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "📊 Статистика")
async def stats(message: Message):
    from database import db
    uid = message.from_user.id
    today = await db.get_today_expenses(uid)
    month = await db.get_month_expenses(uid)
    top = await db.get_top_category(uid)

    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"Сегодня потрачено: <b>{today:,} сум</b>\n"
        f"За месяц потрачено: <b>{month:,} сум</b>\n"
    )
    if top:
        text += f"Топ категория: <b>{top}</b>"
    else:
        text += "Расходов пока нет."

    await message.answer(text)
