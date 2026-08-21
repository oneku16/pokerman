class DomainError(Exception):
    pass


class RoomNotFoundError(DomainError):
    pass


class RoomClosedError(DomainError):
    pass


class DuplicateMembershipError(DomainError):
    pass


class NotRoomMemberError(DomainError):
    pass


class BuyInNotFoundError(DomainError):
    pass


class InvalidBuyInStateError(DomainError):
    pass


class InvalidBuyInAmountError(DomainError):
    def __init__(self, *, amount: int, default_amount: int) -> None:
        self.amount = amount
        self.default_amount = default_amount
        super().__init__(f"buy-in must be greater than {default_amount}, got {amount}")


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
