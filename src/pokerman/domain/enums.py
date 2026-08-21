from enum import StrEnum


class RoomStatus(StrEnum):
    ACTIVE = "active"
    CLOSED = "closed"


class BuyInStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
