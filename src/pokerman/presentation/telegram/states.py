from aiogram.fsm.state import State, StatesGroup


class CreateRoomStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_buy_in = State()


class RoomSettingsStates(StatesGroup):
    waiting_for_new_qr = State()
    waiting_for_new_buy_in = State()
