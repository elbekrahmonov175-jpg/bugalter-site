from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()


class ConvertState(StatesGroup):
    waiting_amount = State()
    waiting_percent = State()


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def _parse_amount(text: str):
    amount = int(text.replace(" ", "").replace(",", ""))
    if amount <= 0:
        raise ValueError
    return amount


def _parse_percent(text: str):
    percent = float(text.replace(",", ".").replace("%", "").strip())
    if percent < 0 or percent > 100:
        raise ValueError
    return percent


@router.message(F.text == "🔄 Обмен нал→карта")
async def convert_start(message: Message, state: FSMContext):
    await state.set_state(ConvertState.waiting_amount)
    await message.answer(
        "🔄 <b>Обмен наличных на карту</b>\n\n"
        "Сколько наличных сумов кидаешь на карту?",
        reply_markup=cancel_keyboard(),
    )


@router.message(ConvertState.waiting_amount, F.text == "❌ Отмена")
@router.message(ConvertState.waiting_percent, F.text == "❌ Отмена")
async def convert_cancel(message: Message, state: FSMContext):
    await state.clear()
    from handlers.start import MAIN_KEYBOARD
    await message.answer("Отменено.", reply_markup=MAIN_KEYBOARD)


@router.message(ConvertState.waiting_amount)
async def convert_amount(message: Message, state: FSMContext):
    try:
        amount = _parse_amount(message.text)
    except ValueError:
        await message.answer("Введи корректную сумму (целое число > 0).")
        return
    await state.update_data(cash_amount=amount)
    await state.set_state(ConvertState.waiting_percent)
    await message.answer("Какой процент комиссии берут за перевод? (например: 2 или 2.5)")


@router.message(ConvertState.waiting_percent)
async def convert_percent(message: Message, state: FSMContext):
    try:
        percent = _parse_percent(message.text)
    except ValueError:
        await message.answer("Введи корректный процент (число от 0 до 100).")
        return

    data = await state.get_data()
    await state.clear()

    from database import db
    result = await db.add_conversion(message.from_user.id, data["cash_amount"], percent)

    from handlers.start import MAIN_KEYBOARD
    await message.answer(
        "✅ <b>Обмен зафиксирован!</b>\n\n"
        f"Наличными: <b>{result['cash_amount']:,} сум</b>\n"
        f"Комиссия: <b>{percent:g}%</b> = <b>{result['fee_amount']:,} сум</b>\n"
        f"Зачислится на карту: <b>{result['net_amount']:,} сум</b>\n\n"
        f"ℹ️ Комиссия <b>{result['fee_amount']:,} сум</b> добавлена в расходы "
        "как «Комиссия за обмен».",
        reply_markup=MAIN_KEYBOARD,
    )
