from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from pokerman.application.use_cases.get_player_history import get_player_history
from pokerman.application.use_cases.get_player_statistics import get_player_statistics
from pokerman.application.use_cases.get_room_dashboard import RoomDashboard, get_room_dashboard
from pokerman.application.use_cases.list_rooms_for_user import list_rooms_for_user
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

router = Router(name="dashboard")

_DASHBOARD_ROOM_CHOICES = 3


async def _load_dashboard_view(
    deps: Deps, *, room_id: int, requesting_telegram_id: int
) -> tuple[RoomDashboard, InlineKeyboardMarkup]:
    dashboard = await get_room_dashboard(
        deps.uow(),
        deps.ledger_query(),
        room_id=room_id,
        requesting_telegram_id=requesting_telegram_id,
    )
    is_admin = dashboard.room.admin_telegram_id == requesting_telegram_id
    keyboard = room_dashboard_keyboard(dashboard.room, is_admin=is_admin)
    return dashboard, keyboard


@router.callback_query(MenuCallback.filter())
async def show_menu(callback: CallbackQuery, deps: Deps, state: FSMContext) -> None:
    assert callback.from_user is not None
    assert isinstance(callback.message, Message)
    await state.clear()
    rooms = await list_rooms_for_user(deps.uow(), telegram_id=callback.from_user.id)
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_keyboard(rooms))
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
    await callback.message.edit_text(format_dashboard(dashboard), reply_markup=keyboard)
    await callback.answer()


@router.message(Command("dashboard"))
async def cmd_dashboard(message: Message, deps: Deps) -> None:
    assert message.from_user is not None
    rooms = await list_rooms_for_user(
        deps.uow(), telegram_id=message.from_user.id, limit=_DASHBOARD_ROOM_CHOICES
    )
    if not rooms:
        await message.answer("You're not in any rooms yet.")
        return
    if len(rooms) > 1:
        await message.answer("Which room?", reply_markup=room_choice_keyboard(rooms))
        return

    room = rooms[0]
    assert room.id is not None
    try:
        dashboard, keyboard = await _load_dashboard_view(
            deps, room_id=room.id, requesting_telegram_id=message.from_user.id
        )
    except DomainError as error:
        await message.answer(describe_error(error))
        return
    await message.answer(format_dashboard(dashboard), reply_markup=keyboard)


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
