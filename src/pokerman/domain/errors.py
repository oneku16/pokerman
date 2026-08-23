from datetime import datetime


class DomainError(Exception):
    pass


class RoomNotFoundError(DomainError):
    pass


class UserNotFoundError(DomainError):
    pass


class RoomClosedError(DomainError):
    pass


class RoomNotClosedError(DomainError):
    pass


class DuplicateMembershipError(DomainError):
    pass


class NotRoomMemberError(DomainError):
    pass


class BuyInNotFoundError(DomainError):
    pass


class InvalidBuyInStateError(DomainError):
    pass


class CashOutAlreadyRecordedError(DomainError):
    pass


class UnauthorizedActionError(DomainError):
    pass


class RoomCodeExhaustedError(DomainError):
    pass


class RoomHasPendingBuyInsError(DomainError):
    def __init__(self, pending_buy_in_ids: list[int]) -> None:
        self.pending_buy_in_ids = pending_buy_in_ids
        super().__init__(
            f"room has {len(pending_buy_in_ids)} pending buy-in(s) that must be resolved first"
        )


class SpendingLimitExceededError(DomainError):
    def __init__(self, *, limit: int, current_total: int, requested_amount: int) -> None:
        self.limit = limit
        self.current_total = current_total
        self.requested_amount = requested_amount
        super().__init__(
            f"buy-in of {requested_amount} would take this room's total to "
            f"{current_total + requested_amount}, over the {limit} limit"
        )


class SpendingLimitChangeTooSoonError(DomainError):
    def __init__(self, next_allowed_at: datetime) -> None:
        self.next_allowed_at = next_allowed_at
        super().__init__(f"spending limit can be changed again after {next_allowed_at.isoformat()}")
