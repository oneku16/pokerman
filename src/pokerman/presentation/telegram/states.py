from aiogram.fsm.state import State, StatesGroup


class CreateRoomStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_buy_in = State()
    waiting_for_duration = State()


class RoomSettingsStates(StatesGroup):
    waiting_for_new_qr = State()
    waiting_for_new_buy_in = State()


class BuyInStates(StatesGroup):
    waiting_for_custom_amount = State()


class RegistrationStates(StatesGroup):
    waiting_for_display_name = State()


class CashOutStates(StatesGroup):
    waiting_for_chip_count = State()


class JoinRoomStates(StatesGroup):
    waiting_for_code = State()


class SettingsStates(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_qr = State()
    waiting_for_new_limit = State()
