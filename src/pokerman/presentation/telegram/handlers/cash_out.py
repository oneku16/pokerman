from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from pokerman.application.use_cases.get_player_history import get_player_history
from pokerman.application.use_cases.get_room import get_room
from pokerman.application.use_cases.record_cash_out import record_cash_out
from pokerman.domain.errors import DomainError
from pokerman.presentation.telegram.callback_data import (
    CashOutConfirmCallback,
    CashOutPromptCallback,
    CashOutReenterCallback,
)
from pokerman.presentation.telegram.deps import Deps
from pokerman.presentation.telegram.error_messages import describe_error
from pokerman.presentation.telegram.formatting import (
    format_cash_out_confirmation,
    format_cash_out_recorded,
)
from pokerman.presentation.telegram.keyboards import cash_out_confirm_keyboard
from pokerman.presentation.telegram.parsing import parse_nonnegative_amount
from pokerman.presentation.telegram.states import CashOutStates

router = Router(name="cash_out")


async def _ask_for_chip_count(message: Message, state: FSMContext, room_id: int) -> None:
    await state.update_data(room_id=room_id)
    await state.set_state(CashOutStates.waiting_for_chip_count)
    await message.answer("How many chips do you have?")


@router.callback_query(CashOutPromptCallback.filter())
async def start_cash_out(
    callback: CallbackQuery, callback_data: CashOutPromptCallback, state: FSMContext
) -> None:
    assert isinstance(callback.message, Message)
    await _ask_for_chip_count(callback.message, state, callback_data.room_id)
    await callback.answer()


@router.callback_query(CashOutReenterCallback.filter())
async def reenter_cash_out(
    callback: CallbackQuery, callback_data: CashOutReenterCallback, state: FSMContext
) -> None:
    assert isinstance(callback.message, Message)
    await _ask_for_chip_count(callback.message, state, callback_data.room_id)
    await callback.answer()


@router.message(CashOutStates.waiting_for_chip_count)
async def receive_chip_count(message: Message, state: FSMContext, deps: Deps) -> None:
    assert message.from_user is not None
    chip_count = parse_nonnegative_amount(message.text or "")
    if chip_count is None:
        await message.answer(
            "Please send a whole number, e.g. 800 (0 is fine if you busted out)."
        )
        return

    data = await state.get_data()
    room_id = data["room_id"]
    await state.clear()

    try:
        history = await get_player_history(
            deps.uow(),
            room_id=room_id,
            target_telegram_id=message.from_user.id,
            requesting_telegram_id=message.from_user.id,
        )
    except DomainError as error:
        await message.answer(describe_error(error))
        return

    await message.answer(
        format_cash_out_confirmation(
            chip_count=chip_count,
            total_spent=history.confirmed_total,
            currency=history.room.currency,
        ),
        reply_markup=cash_out_confirm_keyboard(room_id, chip_count, history.confirmed_total),
    )


@router.callback_query(CashOutConfirmCallback.filter())
async def confirm_cash_out(
    callback: CallbackQuery, callback_data: CashOutConfirmCallback, deps: Deps
) -> None:
    assert callback.from_user is not None
    assert isinstance(callback.message, Message)
    try:
        member = await record_cash_out(
            deps.uow(),
            room_id=callback_data.room_id,
            player_telegram_id=callback.from_user.id,
            chip_count=callback_data.chip_count,
        )
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return

    assert member.final_chip_count is not None
    net_result = member.final_chip_count - callback_data.total_spent
    room = await get_room(deps.uow(), room_id=callback_data.room_id)
    await callback.message.answer(format_cash_out_recorded(net_result, room.currency))
    await callback.answer("Recorded.")
