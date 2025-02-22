import logging
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import time

from bot.freekassa import FreeKassa
from bot.utils.funcs import add_balance_with_notification
from config.parameters_manager import ParametersManager
from db.database import Database


router = Router(name="balance")
db = Database()

freekassa = FreeKassa(
    shop_id=int(ParametersManager.get_parameter("shop_id")),
    secret_word_1=str(ParametersManager.get_parameter("secret_word_1")),
    secret_word_2=str(ParametersManager.get_parameter("secret_word_2")),
)


class DepositStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_payment = State()


@router.callback_query(F.data == "deposit")
async def deposit_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(DepositStates.waiting_for_amount)
    await callback.message.answer(
        "💰 Введите сумму пополнения в рублях (минимум 100₽):\n\n"
        "💳 Оплата происходит через платёжную систему FreeKassa\n"
        "🎉 После оплаты средства автоматически зачислятся на ваш баланс"
    )


@router.message(DepositStates.waiting_for_amount)
async def process_deposit_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 100:
            await message.answer("❌ Минимальная сумма пополнения - 100₽")
            return

        try:
            # Создаем платеж в FreeKassa
            payment = freekassa.generate_payment_url(
                amount=amount,
                order_id=f"{message.from_user.id}_{int(time.time())}",
            )

            logging.debug(f"Платеж создан: {payment}")

            if not payment:
                logging.error(f"Ошибка создания платежа: {message.from_user.id}")
                await message.answer("❌ Ошибка создания платежа. Попробуйте позже.")
                await state.clear()
                return

            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="💳 Оплатить", url=payment)],
                    [
                        types.InlineKeyboardButton(
                            text="❌ Отменить", callback_data="cancel_payment"
                        )
                    ],
                ]
            )

            await message.answer(
                f"💰 Платеж на сумму {amount}₽ создан\n"
                f"ID платежа: {message.from_user.id}_{int(time.time())}\n\n"
                "1. Нажмите кнопку «Оплатить»\n"
                "2. Оплатите счет удобным способом\n"
                "3. Деньги автоматически зачислятся на ваш баланс",
                reply_markup=keyboard,
            )

        except Exception as e:
            logging.error(f"Ошибка создания платежа: {e}")
            await message.answer("❌ Произошла ошибка. Попробуйте позже.")
            await state.clear()

    except ValueError:
        await message.answer("❌ Введите корректную сумму числом")


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Платеж отменен")
