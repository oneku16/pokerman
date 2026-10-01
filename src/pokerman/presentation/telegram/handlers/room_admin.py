from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User

from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.create_room import create_room
from pokerman.application.use_cases.get_room import get_room
from pokerman.application.use_cases.get_room_dashboard import get_room_dashboard
from pokerman.application.use_cases.get_user import get_user
from pokerman.application.use_cases.list_ownership_candidates import list_ownership_candidates
from pokerman.application.use_cases.list_room_members import list_room_members
from pokerman.application.use_cases.transfer_room_ownership import transfer_room_ownership
from pokerman.application.use_cases.update_default_buy_in import update_default_buy_in
from pokerman.application.use_cases.upload_room_qr import upload_room_qr
from pokerman.domain.entities import MAX_PLANNED_DURATION_HOURS
from pokerman.domain.errors import DomainError
from pokerman.presentation.telegram.callback_data import (
    CloseRoomAskCallback,
    CloseRoomConfirmedCallback,
    NewRoomCallback,
    PlayHoursCallback,
    PlayHoursOtherCallback,
    SetDefaultBuyInCallback,
    SetQrCallback,
    TransferOwnershipCallback,
    TransferOwnershipConfirmCallback,
    TransferOwnershipPickCallback,
    UseSavedQrCallback,
)
from pokerman.presentation.telegram.deps import Deps
from pokerman.presentation.telegram.error_messages import describe_error
from pokerman.presentation.telegram.formatting import (
    format_buy_in_notification_for_admin,
    format_cash_out_prompt,
    format_dashboard,
    format_new_host_announcement,
    format_ownership_received,
    format_ownership_transferred,
    format_room_created,
    format_transfer_ownership_prompt,
)
from pokerman.presentation.telegram.handlers.dashboard import build_room_keyboard
from pokerman.presentation.telegram.handlers.start import ensure_registered_or_ask
from pokerman.presentation.telegram.keyboards import (
    admin_confirm_keyboard,
    cancel_keyboard,
    cash_out_prompt_keyboard,
    close_room_confirm_keyboard,
    ownership_candidates_keyboard,
    play_hours_keyboard,
    transfer_ownership_confirm_keyboard,
)
from pokerman.presentation.telegram.messaging import safe_edit_text
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
async def receive_default_buy_in(message: Message, state: FSMContext) -> None:
    amount = parse_positive_amount(message.text or "")
    if amount is None:
        await message.answer(
            "Please send a positive whole number, e.g. 500.", reply_markup=cancel_keyboard()
        )
        return

    await state.update_data(default_buy_in=amount)
    await state.set_state(CreateRoomStates.waiting_for_duration)
    await message.answer(
        "How many hours are you going to play?", reply_markup=play_hours_keyboard()
    )


@router.callback_query(CreateRoomStates.waiting_for_duration, PlayHoursCallback.filter())
async def pick_play_hours(
    callback: CallbackQuery, callback_data: PlayHoursCallback, state: FSMContext, deps: Deps
) -> None:
    assert isinstance(callback.message, Message)
    await callback.answer()
    await _finish_create_room(
        callback.message, callback.from_user, state, deps, hours=callback_data.hours
    )


@router.callback_query(CreateRoomStates.waiting_for_duration, PlayHoursOtherCallback.filter())
async def ask_custom_play_hours(callback: CallbackQuery) -> None:
    assert isinstance(callback.message, Message)
    await callback.message.answer(
        f"Send the number of hours as a whole number, from 1 to {MAX_PLANNED_DURATION_HOURS}.",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(CreateRoomStates.waiting_for_duration)
async def receive_custom_play_hours(message: Message, state: FSMContext, deps: Deps) -> None:
    assert message.from_user is not None
    hours = parse_positive_amount(message.text or "")
    if hours is None or hours > MAX_PLANNED_DURATION_HOURS:
        await message.answer(
            f"Please send a whole number of hours from 1 to {MAX_PLANNED_DURATION_HOURS}.",
            reply_markup=cancel_keyboard(),
        )
        return
    await _finish_create_room(message, message.from_user, state, deps, hours=hours)


@router.callback_query(PlayHoursCallback.filter())
@router.callback_query(PlayHoursOtherCallback.filter())
async def expired_play_hours(callback: CallbackQuery) -> None:
    await callback.answer("This prompt has expired. Start again from the menu.", show_alert=True)


async def _finish_create_room(
    message: Message, author: User, state: FSMContext, deps: Deps, *, hours: int
) -> None:
    data = await state.get_data()
    await state.clear()
    room = await create_room(
        deps.uow(),
        deps.code_generator(),
        admin_telegram_id=author.id,
        admin_username=author.username,
        admin_display_name=author.full_name,
        name=data["room_name"],
        default_buy_in_amount=data["default_buy_in"],
        currency=deps.default_currency,
        planned_duration_hours=hours,
    )

    keyboard = await build_room_keyboard(deps, room, requesting_telegram_id=author.id)
    await message.answer(
        format_room_created(room, deps.bot_username, deps.timezone), reply_markup=keyboard
    )


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


@router.callback_query(TransferOwnershipCallback.filter())
async def start_transfer_ownership(
    callback: CallbackQuery, callback_data: TransferOwnershipCallback, deps: Deps
) -> None:
    assert isinstance(callback.message, Message)
    try:
        candidates = await list_ownership_candidates(
            deps.uow(), room_id=callback_data.room_id, admin_telegram_id=callback.from_user.id
        )
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return
    if not candidates:
        await callback.answer(
            "No other players have joined this room yet.", show_alert=True
        )
        return
    await callback.message.answer(
        "Who should take over as the room's host?",
        reply_markup=ownership_candidates_keyboard(callback_data.room_id, candidates),
    )
    await callback.answer()


@router.callback_query(TransferOwnershipPickCallback.filter())
async def ask_transfer_ownership(
    callback: CallbackQuery, callback_data: TransferOwnershipPickCallback, deps: Deps
) -> None:
    assert isinstance(callback.message, Message)
    try:
        candidates = await list_ownership_candidates(
            deps.uow(), room_id=callback_data.room_id, admin_telegram_id=callback.from_user.id
        )
        room = await get_room(deps.uow(), room_id=callback_data.room_id)
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return
    candidate = next((u for u in candidates if u.telegram_id == callback_data.telegram_id), None)
    if candidate is None:
        await callback.answer("That player isn't in this room anymore.", show_alert=True)
        return
    await safe_edit_text(
        callback.message,
        format_transfer_ownership_prompt(room, candidate.display_name),
        reply_markup=transfer_ownership_confirm_keyboard(
            callback_data.room_id, callback_data.telegram_id
        ),
    )
    await callback.answer()


@router.callback_query(TransferOwnershipConfirmCallback.filter())
async def confirm_transfer_ownership(
    callback: CallbackQuery,
    callback_data: TransferOwnershipConfirmCallback,
    deps: Deps,
    bot: Bot,
) -> None:
    assert isinstance(callback.message, Message)
    try:
        transfer = await transfer_room_ownership(
            deps.uow(),
            room_id=callback_data.room_id,
            admin_telegram_id=callback.from_user.id,
            new_admin_telegram_id=callback_data.telegram_id,
        )
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return

    room = transfer.room
    new_owner = transfer.new_admin
    assert room.id is not None
    old_owner_keyboard = await build_room_keyboard(
        deps, room, requesting_telegram_id=callback.from_user.id
    )
    await safe_edit_text(
        callback.message,
        format_ownership_transferred(room, new_owner.display_name),
        reply_markup=old_owner_keyboard,
    )
    await callback.answer("Ownership transferred.")

    previous_owner = await get_user(deps.uow(), telegram_id=callback.from_user.id)
    previous_name = (
        previous_owner.display_name if previous_owner is not None else callback.from_user.full_name
    )
    new_owner_keyboard = await build_room_keyboard(
        deps, room, requesting_telegram_id=new_owner.telegram_id
    )
    try:
        await bot.send_message(
            new_owner.telegram_id,
            format_ownership_received(room, previous_name),
            reply_markup=new_owner_keyboard,
        )
        for pending in transfer.pending_buy_ins:
            assert pending.buy_in.id is not None
            await bot.send_message(
                new_owner.telegram_id,
                format_buy_in_notification_for_admin(
                    pending.player_display_name, pending.buy_in.amount, room.currency
                ),
                reply_markup=admin_confirm_keyboard(pending.buy_in.id),
            )
    except TelegramAPIError:
        pass

    members = await list_room_members(deps.uow(), room_id=room.id)
    announcement = format_new_host_announcement(room, new_owner.display_name)
    for member in members:
        if member.user_telegram_id in (new_owner.telegram_id, transfer.previous_admin_telegram_id):
            continue
        try:
            await bot.send_message(member.user_telegram_id, announcement)
        except TelegramAPIError:
            continue


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
    await callback.message.answer(format_dashboard(dashboard, deps.timezone))
    await callback.answer("Room closed.")

    members = await list_room_members(deps.uow(), room_id=room.id)
    prompt_text = format_cash_out_prompt(room)
    keyboard = cash_out_prompt_keyboard(room.id)
    for member in members:
        try:
            await bot.send_message(member.user_telegram_id, prompt_text, reply_markup=keyboard)
        except TelegramAPIError:
            continue
