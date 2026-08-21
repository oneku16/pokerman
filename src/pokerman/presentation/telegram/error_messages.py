from pokerman.domain.errors import (
    BuyInNotFoundError,
    DomainError,
    DuplicateMembershipError,
    InvalidBuyInAmountError,
    InvalidBuyInStateError,
    NotRoomMemberError,
    RoomClosedError,
    RoomCodeExhaustedError,
    RoomHasPendingBuyInsError,
    RoomNotFoundError,
    UnauthorizedActionError,
)

_MESSAGES: dict[type[DomainError], str] = {
    RoomNotFoundError: "That room doesn't exist or isn't active anymore.",
    RoomClosedError: "This room is closed and is now read-only.",
    DuplicateMembershipError: "You've already joined this room.",
    NotRoomMemberError: "You need to join this room first.",
    BuyInNotFoundError: "That buy-in request no longer exists.",
    InvalidBuyInStateError: "That buy-in was already resolved.",
    UnauthorizedActionError: "Only the room's admin can do that.",
    RoomCodeExhaustedError: "Couldn't generate a room code right now. Please try again.",
}


def describe_error(error: DomainError) -> str:
    if isinstance(error, RoomHasPendingBuyInsError):
        ids = ", ".join(f"#{i}" for i in error.pending_buy_in_ids)
        return f"Resolve these pending buy-ins before closing the room: {ids}"
    if isinstance(error, InvalidBuyInAmountError):
        if error.is_first_buy_in:
            return f"Your first buy-in must be exactly {error.default_amount}."
        return f"Buy-ins after your first must be more than {error.default_amount}."
    return _MESSAGES.get(type(error), "Something went wrong. Please try again.")
