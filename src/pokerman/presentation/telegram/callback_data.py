from aiogram.filters.callback_data import CallbackData


class MenuCallback(CallbackData, prefix="menu"):
    pass


class NewRoomCallback(CallbackData, prefix="newroom"):
    pass


class RoomCallback(CallbackData, prefix="room"):
    room_id: int


class BuyInCallback(CallbackData, prefix="buyin"):
    room_id: int


class BuyInAmountCallback(CallbackData, prefix="buyinamt"):
    room_id: int
    amount: int


class BuyInOtherCallback(CallbackData, prefix="buyinoth"):
    room_id: int


class PaidCallback(CallbackData, prefix="paid"):
    room_id: int
    amount: int


class ConfirmBuyInCallback(CallbackData, prefix="confirm"):
    buy_in_id: int


class RejectBuyInCallback(CallbackData, prefix="reject"):
    buy_in_id: int


class HistoryCallback(CallbackData, prefix="hist"):
    room_id: int


class SetQrCallback(CallbackData, prefix="setqr"):
    room_id: int


class SetDefaultBuyInCallback(CallbackData, prefix="setbuyin"):
    room_id: int


class CloseRoomAskCallback(CallbackData, prefix="closeask"):
    room_id: int


class CloseRoomConfirmedCallback(CallbackData, prefix="closeok"):
    room_id: int


class CashOutPromptCallback(CallbackData, prefix="cashout"):
    room_id: int


class CashOutConfirmCallback(CallbackData, prefix="cashoutok"):
    room_id: int
    chip_count: int
    total_spent: int


class CashOutReenterCallback(CallbackData, prefix="cashoutre"):
    room_id: int
