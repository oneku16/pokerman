from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.create_room import create_room
from pokerman.application.use_cases.get_room_dashboard import get_room_dashboard
from pokerman.application.use_cases.get_user import get_user
from pokerman.application.use_cases.list_room_members import list_room_members
from pokerman.application.use_cases.update_default_buy_in import update_default_buy_in
from pokerman.application.use_cases.upload_room_qr import upload_room_qr
from pokerman.domain.errors import DomainError
from pokerman.presentation.telegram.callback_data import (
    CloseRoomAskCallback,
    CloseRoomConfirmedCallback,
    NewRoomCallback,
    SetDefaultBuyInCallback,
    SetQrCallback,
    UseSavedQrCallback,
)
from pokerman.presentation.telegram.deps import Deps
from pokerman.presentation.telegram.error_messages import describe_error
from pokerman.presentation.telegram.formatting import (
    format_cash_out_prompt,
    format_dashboard,
    format_room_created,
)
from pokerman.presentation.telegram.handlers.dashboard import build_room_keyboard
from pokerman.presentation.telegram.handlers.start import ensure_registered_or_ask
from pokerman.presentation.telegram.keyboards import (
    cancel_keyboard,
    cash_out_prompt_keyboard,
    close_room_confirm_keyboard,
)
from pokerman.presentation.telegram.parsing import parse_positive_amount
from pokerman.presentation.telegram.states import CreateRoomStates, RoomSettingsStates

router = Router(name="room_admin")


@router.callback_query(NewRoomCallback.filter())
async def start_create_room(callback: CallbackQuery, deps: Deps, state: FSMContext) -> None:
    assert callback.from_user is not None
    assert isinstance(callback.message, Message)
    registered = await ensure_registered_or_ask(
        callback.message,
        telegram_id=callback.from_user.id,
        deps=deps,
        state=state,
        pending_type="create_room",
    )
    if not registered:
        await callback.answer()
        return
    await state.set_state(CreateRoomStates.waiting_for_name)
    await callback.message.answer(
        "What should the room be called?", reply_markup=cancel_keyboard()
    )
    await callback.answer()


@router.message(CreateRoomStates.waiting_for_name)
async def receive_room_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not name:
        await message.answer("Please send a room name as text.", reply_markup=cancel_keyboard())
        return
    await state.update_data(room_name=name)
    await state.set_state(CreateRoomStates.waiting_for_buy_in)
    await message.answer("What's the default buy-in amount?", reply_markup=cancel_keyboard())


@router.message(CreateRoomStates.waiting_for_buy_in)
async def receive_default_buy_in(message: Message, state: FSMContext, deps: Deps) -> None:
    assert message.from_user is not None
    amount = parse_positive_amount(message.text or "")
    if amount is None:
        await message.answer(
            "Please send a positive whole number, e.g. 500.", reply_markup=cancel_keyboard()
        )
        return

    data = await state.get_data()
    room = await create_room(
        deps.uow(),
        deps.code_generator(),
        admin_telegram_id=message.from_user.id,
        admin_username=message.from_user.username,
        admin_display_name=message.from_user.full_name,
        name=data["room_name"],
        default_buy_in_amount=amount,
        currency=deps.default_currency,
    )
    await state.clear()

    keyboard = await build_room_keyboard(deps, room, requesting_telegram_id=message.from_user.id)
    await message.answer(format_room_created(room, deps.bot_username), reply_markup=keyboard)


@router.callback_query(SetQrCallback.filter())
async def start_set_qr(
    callback: CallbackQuery, callback_data: SetQrCallback, state: FSMContext
) -> None:
    assert isinstance(callback.message, Message)
    await state.update_data(room_id=callback_data.room_id)
    await state.set_state(RoomSettingsStates.waiting_for_new_qr)
    await callback.message.answer("Send the new payment QR as a photo.")
    await callback.answer()


@router.message(RoomSettingsStates.waiting_for_new_qr)
async def receive_new_qr(message: Message, state: FSMContext, deps: Deps) -> None:
    assert message.from_user is not None
    if not message.photo:
        await message.answer("Please send the QR as a photo.")
        return

    data = await state.get_data()
    try:
        room = await upload_room_qr(
            deps.uow(),
            room_id=data["room_id"],
            admin_telegram_id=message.from_user.id,
            qr_file_id=message.photo[-1].file_id,
        )
    except DomainError as error:
        await state.clear()
        await message.answer(describe_error(error))
        return

    await state.clear()
    keyboard = await build_room_keyboard(deps, room, requesting_telegram_id=message.from_user.id)
    await message.answer("QR updated.", reply_markup=keyboard)


@router.callback_query(UseSavedQrCallback.filter())
async def use_saved_qr(
    callback: CallbackQuery, callback_data: UseSavedQrCallback, deps: Deps
) -> None:
    assert callback.from_user is not None
    assert isinstance(callback.message, Message)
    admin = await get_user(deps.uow(), telegram_id=callback.from_user.id)
    if admin is None or admin.default_qr_file_id is None:
        await callback.answer("No saved QR on file.", show_alert=True)
        return
    try:
        room = await upload_room_qr(
            deps.uow(),
            room_id=callback_data.room_id,
            admin_telegram_id=callback.from_user.id,
            qr_file_id=admin.default_qr_file_id,
        )
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return
    keyboard = await build_room_keyboard(deps, room, requesting_telegram_id=callback.from_user.id)
    await callback.message.answer("QR updated.", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(SetDefaultBuyInCallback.filter())
async def start_set_default_buy_in(
    callback: CallbackQuery, callback_data: SetDefaultBuyInCallback, state: FSMContext
) -> None:
    assert isinstance(callback.message, Message)
    await state.update_data(room_id=callback_data.room_id)
    await state.set_state(RoomSettingsStates.waiting_for_new_buy_in)
    await callback.message.answer("What's the new default buy-in amount?")
    await callback.answer()


@router.message(RoomSettingsStates.waiting_for_new_buy_in)
async def receive_new_default_buy_in(message: Message, state: FSMContext, deps: Deps) -> None:
    assert message.from_user is not None
    amount = parse_positive_amount(message.text or "")
    if amount is None:
        await message.answer("Please send a positive whole number, e.g. 500.")
        return

    data = await state.get_data()
    try:
        room = await update_default_buy_in(
            deps.uow(),
            room_id=data["room_id"],
            admin_telegram_id=message.from_user.id,
            amount=amount,
        )
    except DomainError as error:
        await state.clear()
        await message.answer(describe_error(error))
        return

    await state.clear()
    keyboard = await build_room_keyboard(deps, room, requesting_telegram_id=message.from_user.id)
    await message.answer(f"Default buy-in is now {amount} {room.currency}.", reply_markup=keyboard)


@router.callback_query(CloseRoomAskCallback.filter())
async def ask_close_room(
    callback: CallbackQuery, callback_data: CloseRoomAskCallback
) -> None:
    assert isinstance(callback.message, Message)
    await callback.message.answer(
        "Close this room? This cannot be undone.",
        reply_markup=close_room_confirm_keyboard(callback_data.room_id),
    )
    await callback.answer()


@router.callback_query(CloseRoomConfirmedCallback.filter())
async def confirm_close_room(
    callback: CallbackQuery, callback_data: CloseRoomConfirmedCallback, deps: Deps, bot: Bot
) -> None:
    assert callback.from_user is not None
    assert isinstance(callback.message, Message)
    try:
        room = await close_room(
            deps.uow(), room_id=callback_data.room_id, admin_telegram_id=callback.from_user.id
        )
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return

    assert room.id is not None
    dashboard = await get_room_dashboard(
        deps.uow(),
        deps.ledger_query(),
        room_id=room.id,
        requesting_telegram_id=callback.from_user.id,
    )
    await callback.message.answer(format_dashboard(dashboard))
    await callback.answer("Room closed.")

    members = await list_room_members(deps.uow(), room_id=room.id)
    prompt_text = format_cash_out_prompt(room)
    keyboard = cash_out_prompt_keyboard(room.id)
    for member in members:
        try:
            await bot.send_message(member.user_telegram_id, prompt_text, reply_markup=keyboard)
        except TelegramAPIError:
            continue
