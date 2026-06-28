from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import EXPENSE_CATEGORIES

router = Router()


class ExpenseState(StatesGroup):
    waiting_category = State()
    waiting_amount = State()


def expense_keyboard():
    buttons = [[KeyboardButton(text=c)] for c in EXPENSE_CATEGORIES]
    buttons.append([KeyboardButton(text="❌ Отмена")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


@router.message(F.text == "➖ Расход")
async def expense_start(message: Message, state: FSMContext):
    await state.set_state(ExpenseState.waiting_category)
    await message.answer("Выбери категорию расхода:", reply_markup=expense_keyboard())


@router.message(ExpenseState.waiting_category, F.text == "❌ Отмена")
async def expense_cancel(message: Message, state: FSMContext):
    await state.clear()
    from handlers.start import MAIN_KEYBOARD
    await message.answer("Отменено.", reply_markup=MAIN_KEYBOARD)


@router.message(ExpenseState.waiting_category)
async def expense_category(message: Message, state: FSMContext):
    if message.text not in EXPENSE_CATEGORIES:
        await message.answer("Выбери категорию из списка.")
        return
    await state.update_data(category=message.text)
    await state.set_state(ExpenseState.waiting_amount)
    await message.answer("Введи сумму (в сумах):", reply_markup=ReplyKeyboardRemove())


@router.message(ExpenseState.waiting_amount)
async def expense_amount(message: Message, state: FSMContext):
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
    await db.add_transaction(message.from_user.id, "expense", data["category"], amount)

    from handlers.start import MAIN_KEYBOARD
    await message.answer(
        f"✅ Расход добавлен!\n"
        f"Категория: <b>{data['category']}</b>\n"
        f"Сумма: <b>{amount:,} сум</b>",
        reply_markup=MAIN_KEYBOARD,
    )
