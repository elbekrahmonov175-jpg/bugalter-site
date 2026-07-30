from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import INCOME_CATEGORIES

router = Router()


class IncomeState(StatesGroup):
    waiting_category = State()
    waiting_amount = State()


def income_keyboard():
    buttons = [[KeyboardButton(text=c)] for c in INCOME_CATEGORIES]
    buttons.append([KeyboardButton(text="❌ Отмена")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@router.message(F.text == "➕ Доход")
async def income_start(message: Message, state: FSMContext):
    await state.set_state(IncomeState.waiting_category)
    await message.answer("Выбери категорию дохода:", reply_markup=income_keyboard())


@router.message(IncomeState.waiting_category, F.text == "❌ Отмена")
async def income_cancel(message: Message, state: FSMContext):
    await state.clear()
    from handlers.start import MAIN_KEYBOARD
    await message.answer("Отменено.", reply_markup=MAIN_KEYBOARD)


@router.message(IncomeState.waiting_category)
async def income_category(message: Message, state: FSMContext):
    if message.text not in INCOME_CATEGORIES:
        await message.answer("Выбери категорию из списка.")
        return
    await state.update_data(category=message.text)
    await state.set_state(IncomeState.waiting_amount)
    await message.answer("Введи сумму (в сумах):", reply_markup=ReplyKeyboardRemove())


@router.message(IncomeState.waiting_amount)
async def income_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи корректную сумму (целое число > 0).")
        return

    data = await state.get_data()
    await state.clear()

    from database import db
    await db.add_transaction(message.from_user.id, "income", data["category"], amount)

    from handlers.start import MAIN_KEYBOARD
    await message.answer(
        f"✅ Доход добавлен!\n"
        f"Категория: <b>{data['category']}</b>\n"
        f"Сумма: <b>{amount:,} сум</b>",
        reply_markup=MAIN_KEYBOARD,
    )
