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


class JoinRoomCallback(CallbackData, prefix="joinroom"):
    pass


class MyStatisticsCallback(CallbackData, prefix="mystats"):
    pass


class SettingsCallback(CallbackData, prefix="settings"):
    pass


class ChangeNameCallback(CallbackData, prefix="chgname"):
    pass


class SetDefaultQrCallback(CallbackData, prefix="setdefqr"):
    pass


class SetSpendingLimitCallback(CallbackData, prefix="setlimit"):
    pass


class UseSavedQrCallback(CallbackData, prefix="usesavedqr"):
    room_id: int


class PlayHoursCallback(CallbackData, prefix="playhrs"):
    hours: int


class PlayHoursOtherCallback(CallbackData, prefix="playhrsoth"):
    pass


class TransferOwnershipCallback(CallbackData, prefix="xfer"):
    room_id: int


class TransferOwnershipPickCallback(CallbackData, prefix="xferpick"):
    room_id: int
    telegram_id: int


class TransferOwnershipConfirmCallback(CallbackData, prefix="xferok"):
    room_id: int
    telegram_id: int
