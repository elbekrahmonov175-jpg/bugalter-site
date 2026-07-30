from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "💰 Баланс")
async def balance(message: Message):
    from database import db
    bal = await db.get_balance(message.from_user.id)
    await message.answer(
        f"💰 <b>Ваш баланс</b>\n\n"
        f"📈 Доходы: <b>{bal['income']:,} сум</b>\n"
        f"📉 Расходы: <b>{bal['expense']:,} сум</b>\n"
        f"💵 Остаток: <b>{bal['balance']:,} сум</b>"
    )
