from aiogram import Router
from aiogram.types import CallbackQuery, Message

from pokerman.application.use_cases.get_player_history import get_player_history
from pokerman.application.use_cases.get_room_dashboard import get_room_dashboard
from pokerman.application.use_cases.list_rooms_for_user import list_rooms_for_user
from pokerman.domain.errors import DomainError
from pokerman.presentation.telegram.callback_data import HistoryCallback, MenuCallback, RoomCallback
from pokerman.presentation.telegram.deps import Deps
from pokerman.presentation.telegram.error_messages import describe_error
from pokerman.presentation.telegram.formatting import format_dashboard, format_player_history
from pokerman.presentation.telegram.handlers.start import WELCOME_TEXT
from pokerman.presentation.telegram.keyboards import main_menu_keyboard, room_dashboard_keyboard

router = Router(name="dashboard")


@router.callback_query(MenuCallback.filter())
async def show_menu(callback: CallbackQuery, deps: Deps) -> None:
    assert callback.from_user is not None
    assert isinstance(callback.message, Message)
    rooms = await list_rooms_for_user(deps.uow(), telegram_id=callback.from_user.id)
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=main_menu_keyboard(rooms))
    await callback.answer()


@router.callback_query(RoomCallback.filter())
async def show_room_dashboard(
    callback: CallbackQuery, callback_data: RoomCallback, deps: Deps
) -> None:
    assert callback.from_user is not None
    assert isinstance(callback.message, Message)
    try:
        dashboard = await get_room_dashboard(
            deps.uow(),
            deps.ledger_query(),
            room_id=callback_data.room_id,
            requesting_telegram_id=callback.from_user.id,
        )
    except DomainError as error:
        await callback.answer(describe_error(error), show_alert=True)
        return
    is_admin = dashboard.room.admin_telegram_id == callback.from_user.id
    await callback.message.edit_text(
        format_dashboard(dashboard),
        reply_markup=room_dashboard_keyboard(dashboard.room, is_admin=is_admin),
    )
    await callback.answer()


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
