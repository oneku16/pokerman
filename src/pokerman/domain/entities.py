from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from pokerman.domain.enums import BuyInStatus, RoomStatus
from pokerman.domain.errors import (
    CashOutAlreadyRecordedError,
    InvalidBuyInStateError,
    InvalidOwnershipTransferError,
    RoomClosedError,
    SpendingLimitChangeTooSoonError,
)
from pokerman.domain.value_objects import RoomCode

SPENDING_LIMIT_COOLDOWN = timedelta(days=7)
MAX_PLANNED_DURATION_HOURS = 24


@dataclass(slots=True)
class User:
    telegram_id: int
    username: str | None
    display_name: str
    created_at: datetime
    default_qr_file_id: str | None = None
    spending_limit: int | None = None
    spending_limit_updated_at: datetime | None = None

    @classmethod
    def register(
        cls, *, telegram_id: int, username: str | None, display_name: str, now: datetime
    ) -> User:
        return cls(
            telegram_id=telegram_id,
            username=username,
            display_name=display_name,
            created_at=now,
        )

    def refresh_profile(self, *, username: str | None) -> None:
        self.username = username

    def rename(self, display_name: str) -> None:
        if not display_name.strip():
            raise ValueError("display name must not be blank")
        self.display_name = display_name

    def set_default_qr(self, qr_file_id: str) -> None:
        self.default_qr_file_id = qr_file_id

    def set_spending_limit(self, limit: int, now: datetime) -> None:
        if limit <= 0:
            raise ValueError("spending limit must be positive")
        if self.spending_limit_updated_at is not None:
            next_allowed_at = self.spending_limit_updated_at + SPENDING_LIMIT_COOLDOWN
            if now < next_allowed_at:
                raise SpendingLimitChangeTooSoonError(next_allowed_at)
        self.spending_limit = limit
        self.spending_limit_updated_at = now


@dataclass(slots=True)
class RoomPlayer:
    id: int | None
    room_id: int
    user_telegram_id: int
    joined_at: datetime
    final_chip_count: int | None = None
    cashed_out_at: datetime | None = None

    @classmethod
    def join(cls, *, room_id: int, user_telegram_id: int, now: datetime) -> RoomPlayer:
        return cls(id=None, room_id=room_id, user_telegram_id=user_telegram_id, joined_at=now)

    def record_cash_out(self, chip_count: int, now: datetime) -> None:
        if self.final_chip_count is not None:
            raise CashOutAlreadyRecordedError(
                f"room player {self.id} already recorded a cash-out"
            )
        if chip_count < 0:
            raise ValueError("chip count cannot be negative")
        self.final_chip_count = chip_count
        self.cashed_out_at = now


@dataclass(slots=True)
class BuyIn:
    id: int | None
    room_player_id: int
    amount: int
    status: BuyInStatus
    requested_at: datetime
    decided_at: datetime | None = None
    decided_by_telegram_id: int | None = None

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError("buy-in amount must be positive")

    @classmethod
    def request(cls, *, room_player_id: int, amount: int, now: datetime) -> BuyIn:
        return cls(
            id=None,
            room_player_id=room_player_id,
            amount=amount,
            status=BuyInStatus.PENDING,
            requested_at=now,
        )

    def confirm(self, *, decided_by_telegram_id: int, now: datetime) -> None:
        self._ensure_pending("confirm")
        self.status = BuyInStatus.CONFIRMED
        self.decided_at = now
        self.decided_by_telegram_id = decided_by_telegram_id

    def reject(self, *, decided_by_telegram_id: int, now: datetime) -> None:
        self._ensure_pending("reject")
        self.status = BuyInStatus.REJECTED
        self.decided_at = now
        self.decided_by_telegram_id = decided_by_telegram_id

    def _ensure_pending(self, action: str) -> None:
        if self.status != BuyInStatus.PENDING:
            raise InvalidBuyInStateError(
                f"cannot {action} buy-in {self.id}: already {self.status.value}"
            )


@dataclass(slots=True)
class PokerRoom:
    id: int | None
    name: str
    code: RoomCode
    deep_link_token: str
    default_buy_in_amount: int
    currency: str
    admin_telegram_id: int
    status: RoomStatus
    qr_file_id: str | None
    created_at: datetime
    closed_at: datetime | None = None
    planned_duration_hours: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("room name must not be blank")
        if self.default_buy_in_amount <= 0:
            raise ValueError("default buy-in amount must be positive")
        if self.planned_duration_hours is not None and not (
            1 <= self.planned_duration_hours <= MAX_PLANNED_DURATION_HOURS
        ):
            raise ValueError(
                f"planned duration must be between 1 and {MAX_PLANNED_DURATION_HOURS} hours"
            )

    @property
    def planned_end_at(self) -> datetime | None:
        if self.planned_duration_hours is None:
            return None
        return self.created_at + timedelta(hours=self.planned_duration_hours)

    @classmethod
    def open(
        cls,
        *,
        name: str,
        code: RoomCode,
        deep_link_token: str,
        default_buy_in_amount: int,
        currency: str,
        admin_telegram_id: int,
        now: datetime,
        planned_duration_hours: int | None = None,
    ) -> PokerRoom:
        return cls(
            id=None,
            name=name,
            code=code,
            deep_link_token=deep_link_token,
            default_buy_in_amount=default_buy_in_amount,
            currency=currency,
            admin_telegram_id=admin_telegram_id,
            status=RoomStatus.ACTIVE,
            qr_file_id=None,
            created_at=now,
            planned_duration_hours=planned_duration_hours,
        )

    def ensure_active(self) -> None:
        if self.status != RoomStatus.ACTIVE:
            raise RoomClosedError(f"room {self.id} is closed")

    def set_qr(self, qr_file_id: str) -> None:
        self.ensure_active()
        self.qr_file_id = qr_file_id

    def update_default_buy_in(self, amount: int) -> None:
        self.ensure_active()
        if amount <= 0:
            raise ValueError("default buy-in amount must be positive")
        self.default_buy_in_amount = amount

    def transfer_ownership(self, new_admin_telegram_id: int) -> None:
        self.ensure_active()
        if new_admin_telegram_id == self.admin_telegram_id:
            raise InvalidOwnershipTransferError(
                f"user {new_admin_telegram_id} already owns room {self.id}"
            )
        self.admin_telegram_id = new_admin_telegram_id
        # The QR is where players send money, so it belongs to the outgoing host.
        self.qr_file_id = None

    def close(self, now: datetime) -> None:
        self.ensure_active()
        self.status = RoomStatus.CLOSED
        self.closed_at = now
