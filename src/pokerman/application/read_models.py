from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlayerLedgerRow:
    room_player_id: int
    user_telegram_id: int
    display_name: str
    confirmed_total: int
    confirmed_count: int
