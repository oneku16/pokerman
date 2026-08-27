from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from pokerman.application.use_cases.get_current_or_last_room import get_current_or_last_room
from pokerman.application.use_cases.get_player_history import get_player_history
from pokerman.application.use_cases.get_player_statistics import get_player_statistics
from pokerman.application.use_cases.get_room_dashboard import RoomDashboard, get_room_dashboard
from pokerman.application.use_cases.get_user import get_user
from pokerman.application.use_cases.list_rooms_for_user import list_rooms_for_user
from pokerman.domain.entities import PokerRoom
from pokerman.domain.errors import DomainError
from pokerman.presentation.telegram.callback_data import (
    HistoryCallback,
    MenuCallback,
    MyStatisticsCallback,
    RoomCallback,
)
from pokerman.presentation.telegram.deps import Deps
from pokerman.presentation.telegram.error_messages import describe_error
from pokerman.presentation.telegram.formatting import (
    format_dashboard,
    format_player_history,
    format_statistics,
)
from pokerman.presentation.telegram.handlers.start import WELCOME_TEXT
from pokerman.presentation.telegram.keyboards import (
    main_menu_keyboard,
    room_choice_keyboard,
    room_dashboard_keyboard,
)
from pokerman.presentation.telegram.messaging import safe_edit_text

router = Router(name="dashboard")

_HISTORY_ROOM_LIMIT = 10


async def build_room_keyboard(
    deps: Deps, room: PokerRoom, *, requesting_telegram_id: int
) -> InlineKeyboardMarkup:
    is_admin = room.admin_telegram_id == requesting_telegram_id
    offer_saved_qr = False
    if is_admin:
        admin = await get_user(deps.uow(), telegram_id=requesting_telegram_id)
        offer_saved_qr = admin is not None and admin.default_qr_file_id is not None
    return room_dashboard_keyboard(room, is_admin=is_admin, offer_saved_qr=offer_saved_qr)


async def _load_dashboard_view(
    deps: Deps, *, room_id: int, requesting_telegram_id: int
) -> tuple[RoomDashboard, InlineKeyboardMarkup]:
    dashboard = await get_room_dashboard(
        deps.uow(),
        deps.ledger_query(),
        room_id=room_id,
        requesting_telegram_id=requesting_telegram_id,
    )
    keyboard = await build_room_keyboard(
        deps, dashboard.room, requesting_telegram_id=requesting_telegram_id
    )
    return dashboard, keyboard


@router.callback_query(MenuCallback.filter())
async def show_menu(callback: CallbackQuery, state: FSMContext) -> None:
    assert isinstance(callback.message, Message)
    await state.clear()
    await safe_edit_text(callback.message, WELCOME_TEXT, reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(MyStatisticsCallback.filter())
async def show_my_statistics(callback: CallbackQuery, deps: Deps) -> None:
    assert callback.from_user is not None
    assert isinstance(callback.message, Message)
    stats = await get_player_statistics(deps.stats_query(), telegram_id=callback.from_user.id)
    await callback.message.answer(format_statistics(stats, deps.default_currency))
    await callback.answer()


@router.callback_query(RoomCallback.filter())
async def show_room_dashboard(
    callback: CallbackQuery, callback_data: RoomCallback, deps: Deps
) -> None:
    assert callback.from_user is not None
    assert isinstance(callback.message, Message)
    try:
        dashboard, keyboard = await _load_dashboard_view(
            deps, room_id=callback_data.room_id, requesting_telegram_id=callback.from_user.id
        )
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return
    await safe_edit_text(callback.message, format_dashboard(dashboard), reply_markup=keyboard)
    await callback.answer()


@router.message(Command("dashboard"))
async def cmd_dashboard(message: Message, deps: Deps) -> None:
    assert message.from_user is not None
    room = await get_current_or_last_room(deps.uow(), telegram_id=message.from_user.id)
    if room is None:
        await message.answer("You haven't played any rooms yet.")
        return

    assert room.id is not None
    try:
        dashboard, keyboard = await _load_dashboard_view(
            deps, room_id=room.id, requesting_telegram_id=message.from_user.id
        )
    except DomainError as error:
        await message.answer(describe_error(error))
        return
    await message.answer(format_dashboard(dashboard), reply_markup=keyboard)


@router.message(Command("history"))
async def cmd_history(message: Message, deps: Deps) -> None:
    assert message.from_user is not None
    rooms = await list_rooms_for_user(
        deps.uow(), telegram_id=message.from_user.id, limit=_HISTORY_ROOM_LIMIT
    )
    if not rooms:
        await message.answer("You haven't played any rooms yet.")
        return
    await message.answer(
        "Your last rooms — pick one to see its results:",
        reply_markup=room_choice_keyboard(rooms),
    )


@router.message(Command("statistics"))
async def cmd_statistics(message: Message, deps: Deps) -> None:
    assert message.from_user is not None
    stats = await get_player_statistics(deps.stats_query(), telegram_id=message.from_user.id)
    await message.answer(format_statistics(stats, deps.default_currency))


@router.callback_query(HistoryCallback.filter())
async def show_history(callback: CallbackQuery, callback_data: HistoryCallback, deps: Deps) -> None:
    assert callback.from_user is not None
    try:
        history = await get_player_history(
            deps.uow(),
            room_id=callback_data.room_id,
            target_telegram_id=callback.from_user.id,
            requesting_telegram_id=callback.from_user.id,
        )
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return
    assert isinstance(callback.message, Message)
    await callback.message.answer(
        format_player_history(history, display_name=callback.from_user.full_name)
    )
    await callback.answer()
