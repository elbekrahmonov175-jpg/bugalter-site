from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

router = Router()


class DebtState(StatesGroup):
    waiting_type = State()
    waiting_name = State()
    waiting_amount = State()


def debt_type_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💸 Я должен"), KeyboardButton(text="💰 Мне должны")],
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
    )


@router.message(F.text == "🤝 Долги")
async def debts_menu(message: Message, state: FSMContext):
    await state.set_state(DebtState.waiting_type)
    await message.answer("Выбери тип долга:", reply_markup=debt_type_keyboard())


@router.message(DebtState.waiting_type, F.text == "❌ Отмена")
async def debt_cancel(message: Message, state: FSMContext):
    await state.clear()
    from handlers.start import MAIN_KEYBOARD
    await message.answer("Отменено.", reply_markup=MAIN_KEYBOARD)


@router.message(DebtState.waiting_type)
async def debt_type(message: Message, state: FSMContext):
    if message.text == "💸 Я должен":
        dtype = "owe"
    elif message.text == "💰 Мне должны":
        dtype = "lend"
    else:
        await message.answer("Выбери из списка.")
        return
    await state.update_data(type=dtype)
    await state.set_state(DebtState.waiting_name)
    await message.answer("Введи имя человека:", reply_markup=ReplyKeyboardRemove())


@router.message(DebtState.waiting_name)
async def debt_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(DebtState.waiting_amount)
    await message.answer("Введи сумму (в сумах):")


@router.message(DebtState.waiting_amount)
async def debt_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text.replace(" ", "").replace(",", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи корректную сумму.")
        return

    data = await state.get_data()
    await state.clear()

    from database import db
    await db.add_debt(message.from_user.id, data["name"], amount, data["type"])

    label = "Я должен" if data["type"] == "owe" else "Мне должны"
    from handlers.start import MAIN_KEYBOARD
    await message.answer(
        f"✅ Долг записан!\n{label}: <b>{data['name']}</b> — <b>{amount:,} сум</b>",
        reply_markup=MAIN_KEYBOARD,
    )
