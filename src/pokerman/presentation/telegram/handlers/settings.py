from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from pokerman.application.use_cases.get_user import get_user
from pokerman.application.use_cases.set_default_qr import set_default_qr
from pokerman.application.use_cases.set_spending_limit import set_spending_limit
from pokerman.application.use_cases.update_display_name import update_display_name
from pokerman.domain.errors import DomainError, UserNotFoundError
from pokerman.presentation.telegram.callback_data import (
    ChangeNameCallback,
    SetDefaultQrCallback,
    SetSpendingLimitCallback,
    SettingsCallback,
)
from pokerman.presentation.telegram.deps import Deps
from pokerman.presentation.telegram.error_messages import describe_error
from pokerman.presentation.telegram.formatting import format_settings
from pokerman.presentation.telegram.handlers.start import _MAX_NAME_LENGTH
from pokerman.presentation.telegram.keyboards import cancel_keyboard, settings_keyboard
from pokerman.presentation.telegram.parsing import parse_positive_amount
from pokerman.presentation.telegram.states import SettingsStates

router = Router(name="settings")


async def _show_settings(message: Message, deps: Deps, *, telegram_id: int) -> None:
    user = await get_user(deps.uow(), telegram_id=telegram_id)
    if user is None:
        raise UserNotFoundError(f"user {telegram_id} is not registered")
    await message.answer(
        format_settings(user, deps.default_currency),
        reply_markup=settings_keyboard(has_saved_qr=user.default_qr_file_id is not None),
    )


@router.message(Command("settings"))
async def cmd_settings(message: Message, deps: Deps, state: FSMContext) -> None:
    assert message.from_user is not None
    await state.clear()
    try:
        await _show_settings(message, deps, telegram_id=message.from_user.id)
    except DomainError as error:
        await message.answer(describe_error(error))


@router.callback_query(SettingsCallback.filter())
async def show_settings(callback: CallbackQuery, deps: Deps, state: FSMContext) -> None:
    assert callback.from_user is not None
    assert isinstance(callback.message, Message)
    await state.clear()
    try:
        await _show_settings(callback.message, deps, telegram_id=callback.from_user.id)
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return
    await callback.answer()


@router.callback_query(ChangeNameCallback.filter())
async def start_change_name(callback: CallbackQuery, state: FSMContext) -> None:
    assert isinstance(callback.message, Message)
    await state.set_state(SettingsStates.waiting_for_new_name)
    await callback.message.answer("What's your new name?", reply_markup=cancel_keyboard())
    await callback.answer()


@router.message(SettingsStates.waiting_for_new_name)
async def receive_new_name(message: Message, state: FSMContext, deps: Deps) -> None:
    assert message.from_user is not None
    name = (message.text or "").strip()
    if not name:
        await message.answer("Please send your name as text.", reply_markup=cancel_keyboard())
        return
    if len(name) > _MAX_NAME_LENGTH:
        await message.answer(
            f"That's a bit long — please send a shorter name (up to {_MAX_NAME_LENGTH} "
            "characters).",
            reply_markup=cancel_keyboard(),
        )
        return

    await update_display_name(deps.uow(), telegram_id=message.from_user.id, new_name=name)
    await state.clear()
    await message.answer("Name updated.")
    await _show_settings(message, deps, telegram_id=message.from_user.id)


@router.callback_query(SetDefaultQrCallback.filter())
async def start_set_default_qr(callback: CallbackQuery, state: FSMContext) -> None:
    assert isinstance(callback.message, Message)
    await state.set_state(SettingsStates.waiting_for_new_qr)
    await callback.message.answer(
        "Send a photo to use as your saved payment QR.", reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(SettingsStates.waiting_for_new_qr)
async def receive_new_default_qr(message: Message, state: FSMContext, deps: Deps) -> None:
    assert message.from_user is not None
    if not message.photo:
        await message.answer("Please send the QR as a photo.", reply_markup=cancel_keyboard())
        return

    await set_default_qr(
        deps.uow(), telegram_id=message.from_user.id, qr_file_id=message.photo[-1].file_id
    )
    await state.clear()
    await message.answer("Saved QR updated.")
    await _show_settings(message, deps, telegram_id=message.from_user.id)


@router.callback_query(SetSpendingLimitCallback.filter())
async def start_set_spending_limit(callback: CallbackQuery, state: FSMContext) -> None:
    assert isinstance(callback.message, Message)
    await state.set_state(SettingsStates.waiting_for_new_limit)
    await callback.message.answer(
        "What's your new spending limit per room? Send a whole number.",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(SettingsStates.waiting_for_new_limit)
async def receive_new_spending_limit(message: Message, state: FSMContext, deps: Deps) -> None:
    assert message.from_user is not None
    limit = parse_positive_amount(message.text or "")
    if limit is None:
        await message.answer(
            "Please send a positive whole number, e.g. 500.", reply_markup=cancel_keyboard()
        )
        return

    try:
        await set_spending_limit(deps.uow(), telegram_id=message.from_user.id, limit=limit)
    except DomainError as error:
        await state.clear()
        await message.answer(describe_error(error))
        await _show_settings(message, deps, telegram_id=message.from_user.id)
        return

    await state.clear()
    await message.answer(f"Spending limit set to {limit} {deps.default_currency}.")
    await _show_settings(message, deps, telegram_id=message.from_user.id)
