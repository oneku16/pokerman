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
    def __init__(self, *, amount: int, is_first_buy_in: bool, default_amount: int) -> None:
        self.amount = amount
        self.is_first_buy_in = is_first_buy_in
        self.default_amount = default_amount
        if is_first_buy_in:
            message = f"first buy-in must be exactly {default_amount}, got {amount}"
        else:
            message = f"buy-in must be greater than {default_amount}, got {amount}"
        super().__init__(message)


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
