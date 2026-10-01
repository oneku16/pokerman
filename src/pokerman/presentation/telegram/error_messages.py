from pokerman.domain.errors import (
    BuyInNotFoundError,
    CashOutAlreadyRecordedError,
    DomainError,
    DuplicateMembershipError,
    InvalidBuyInStateError,
    InvalidOwnershipTransferError,
    NotRoomMemberError,
    RoomClosedError,
    RoomCodeExhaustedError,
    RoomHasPendingBuyInsError,
    RoomNotClosedError,
    RoomNotFoundError,
    SpendingLimitChangeTooSoonError,
    SpendingLimitExceededError,
    UnauthorizedActionError,
    UserNotFoundError,
)

_MESSAGES: dict[type[DomainError], str] = {
    RoomNotFoundError: "That room doesn't exist or isn't active anymore.",
    RoomClosedError: "This room is closed and is now read-only.",
    RoomNotClosedError: "This room is still open.",
    DuplicateMembershipError: "You've already joined this room.",
    NotRoomMemberError: "You need to join this room first.",
    BuyInNotFoundError: "That buy-in request no longer exists.",
    InvalidBuyInStateError: "That buy-in was already resolved.",
    CashOutAlreadyRecordedError: "You've already recorded your chips for this room.",
    UnauthorizedActionError: "Only the room's admin can do that.",
    RoomCodeExhaustedError: "Couldn't generate a room code right now. Please try again.",
    UserNotFoundError: "Send /start first so I know who you are.",
    InvalidOwnershipTransferError: "That player already owns this room.",
}


def describe_error(error: DomainError) -> str:
    if isinstance(error, RoomHasPendingBuyInsError):
        ids = ", ".join(f"#{i}" for i in error.pending_buy_in_ids)
        return f"Resolve these pending buy-ins before closing the room: {ids}"
    if isinstance(error, SpendingLimitExceededError):
        remaining = max(0, error.limit - error.current_total)
        return (
            f"That would put you over your {error.limit} spending limit for this room "
            f"(you're at {error.current_total}). You can still buy in for up to {remaining}."
        )
    if isinstance(error, SpendingLimitChangeTooSoonError):
        when = error.next_allowed_at.strftime("%d %b %Y")
        return f"Your spending limit can only be changed once a week. Next change: {when}."
    return _MESSAGES.get(type(error), "Something went wrong. Please try again.")
