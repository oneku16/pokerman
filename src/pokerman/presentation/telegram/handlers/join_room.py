from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from pokerman.presentation.telegram.callback_data import JoinRoomCallback
from pokerman.presentation.telegram.deps import Deps
from pokerman.presentation.telegram.handlers.start import (
    _complete_code_join,
    ensure_registered_or_ask,
)
from pokerman.presentation.telegram.keyboards import cancel_keyboard
from pokerman.presentation.telegram.states import JoinRoomStates

router = Router(name="join_room")


@router.callback_query(JoinRoomCallback.filter())
async def start_join_room(callback: CallbackQuery, deps: Deps, state: FSMContext) -> None:
    assert callback.from_user is not None
    assert isinstance(callback.message, Message)
    registered = await ensure_registered_or_ask(
        callback.message,
        telegram_id=callback.from_user.id,
        deps=deps,
        state=state,
        pending_type="menu",
    )
    if not registered:
        await callback.answer()
        return
    await state.set_state(JoinRoomStates.waiting_for_code)
    await callback.message.answer(
        "Send the room's 4-digit code.", reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(JoinRoomStates.waiting_for_code)
async def receive_join_code(message: Message, state: FSMContext, deps: Deps) -> None:
    assert message.from_user is not None
    code = (message.text or "").strip()
    if not code:
        await message.answer("Please send the code as text.", reply_markup=cancel_keyboard())
        return

    room = await _complete_code_join(
        message,
        deps,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        display_name=message.from_user.full_name,
        code=code,
    )
    if room is None:
        await message.answer(
            "Send a valid 4-digit code, or Cancel.", reply_markup=cancel_keyboard()
        )
        return
    await state.clear()
