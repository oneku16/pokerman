from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlayerLedgerRow:
    room_player_id: int
    user_telegram_id: int
    display_name: str
    confirmed_total: int
    confirmed_count: int
    final_chip_count: int | None = None

    @property
    def current_value(self) -> int:
        return self.confirmed_total if self.final_chip_count is None else self.final_chip_count

    @property
    def net_result(self) -> int:
        return self.current_value - self.confirmed_total


@dataclass(frozen=True, slots=True)
class PlayerStatistics:
    telegram_id: int
    display_name: str
    games_played: int
    total_buy_in_count: int
    total_spent: int
    total_cashed_out: int
    net_result: int
