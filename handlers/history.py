from aiogram import Router, F
from aiogram.types import Message

router = Router()

EMOJI = {"income": "📈", "expense": "📉"}


@router.message(F.text == "📜 История")
async def history(message: Message):
    from database import db
    records = await db.get_history(message.from_user.id, limit=10)
    if not records:
        await message.answer("История транзакций пуста.")
        return

    lines = ["📜 <b>Последние 10 транзакций</b>\n"]
    for r in records:
        em = EMOJI.get(r["type"], "💸")
        dt = r["date"].strftime("%d.%m %H:%M") if hasattr(r["date"], "strftime") else str(r["date"])[:16]
        lines.append(f"{em} {r['category']} — <b>{r['amount']:,} сум</b> <i>({dt})</i>")

    await message.answer("\n".join(lines))
