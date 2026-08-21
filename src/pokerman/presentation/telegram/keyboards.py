from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from pokerman.domain.entities import PokerRoom
from pokerman.domain.enums import RoomStatus
from pokerman.presentation.telegram.callback_data import (
    BuyInAmountCallback,
    BuyInCallback,
    BuyInOtherCallback,
    CloseRoomAskCallback,
    CloseRoomConfirmedCallback,
    ConfirmBuyInCallback,
    HistoryCallback,
    MenuCallback,
    NewRoomCallback,
    PaidCallback,
    RejectBuyInCallback,
    RoomCallback,
    SetDefaultBuyInCallback,
    SetQrCallback,
)

PRESET_BUY_IN_AMOUNTS = (200, 400, 500, 600, 1000)


def main_menu_keyboard(rooms: list[PokerRoom]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for room in rooms:
        assert room.id is not None
        builder.button(
            text=f"{room.name} ({room.status.value})",
            callback_data=RoomCallback(room_id=room.id),
        )
    builder.button(text="Create Room", callback_data=NewRoomCallback())
    builder.adjust(1)
    return builder.as_markup()


def room_dashboard_keyboard(room: PokerRoom, *, is_admin: bool) -> InlineKeyboardMarkup:
    assert room.id is not None
    builder = InlineKeyboardBuilder()
    builder.button(text="Dashboard", callback_data=RoomCallback(room_id=room.id))
    if room.status == RoomStatus.ACTIVE:
        builder.button(text="Buy In", callback_data=BuyInCallback(room_id=room.id))
    builder.button(text="My History", callback_data=HistoryCallback(room_id=room.id))
    if is_admin and room.status == RoomStatus.ACTIVE:
        builder.button(text="Change QR", callback_data=SetQrCallback(room_id=room.id))
        builder.button(
            text="Change Default Buy-In", callback_data=SetDefaultBuyInCallback(room_id=room.id)
        )
        builder.button(text="Close Room", callback_data=CloseRoomAskCallback(room_id=room.id))
    builder.button(text="Back", callback_data=MenuCallback())
    builder.adjust(1)
    return builder.as_markup()


def buy_in_amount_keyboard(room_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for amount in PRESET_BUY_IN_AMOUNTS:
        builder.button(
            text=str(amount), callback_data=BuyInAmountCallback(room_id=room_id, amount=amount)
        )
    builder.button(text="Other", callback_data=BuyInOtherCallback(room_id=room_id))
    builder.adjust(3, 2, 1)
    return builder.as_markup()


def buy_in_keyboard(room_id: int, amount: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="I Paid", callback_data=PaidCallback(room_id=room_id, amount=amount))
    builder.adjust(1)
    return builder.as_markup()


def admin_confirm_keyboard(buy_in_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Confirm", callback_data=ConfirmBuyInCallback(buy_in_id=buy_in_id))
    builder.button(text="Reject", callback_data=RejectBuyInCallback(buy_in_id=buy_in_id))
    builder.adjust(2)
    return builder.as_markup()


def close_room_confirm_keyboard(room_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Yes, close it", callback_data=CloseRoomConfirmedCallback(room_id=room_id))
    builder.button(text="Cancel", callback_data=RoomCallback(room_id=room_id))
    builder.adjust(1)
    return builder.as_markup()
