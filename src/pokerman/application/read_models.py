from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlayerLedgerRow:
    room_player_id: int
    user_telegram_id: int
    display_name: str
    confirmed_total: int
    confirmed_count: int


@dataclass(frozen=True, slots=True)
class PlayerStatistics:
    telegram_id: int
    display_name: str
    games_played: int
    total_buy_in_count: int
    total_spent: int
    total_cashed_out: int
    net_result: int
