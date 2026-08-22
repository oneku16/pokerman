from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from pokerman.domain.enums import BuyInStatus, RoomStatus


class Base(DeclarativeBase):
    pass


def _enum_column(enum_cls: type, name: str) -> Enum:
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


class UserModel(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None]
    display_name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PokerRoomModel(Base):
    __tablename__ = "poker_rooms"
    __table_args__ = (
        UniqueConstraint("deep_link_token", name="uq_poker_rooms_deep_link_token"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    code: Mapped[str] = mapped_column(String(4))
    deep_link_token: Mapped[str]
    default_buy_in_amount: Mapped[int]
    currency: Mapped[str] = mapped_column(String(8))
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    status: Mapped[RoomStatus] = mapped_column(_enum_column(RoomStatus, "room_status"))
    qr_file_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index(
    "ix_poker_rooms_active_code",
    PokerRoomModel.code,
    unique=True,
    postgresql_where=(PokerRoomModel.status == RoomStatus.ACTIVE.value),
)


class RoomPlayerModel(Base):
    __tablename__ = "room_players"
    __table_args__ = (
        UniqueConstraint("room_id", "user_telegram_id", name="uq_room_players_room_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("poker_rooms.id"))
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"))
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    final_chip_count: Mapped[int | None]
    cashed_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BuyInModel(Base):
    __tablename__ = "buy_ins"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_player_id: Mapped[int] = mapped_column(ForeignKey("room_players.id"))
    amount: Mapped[int]
    status: Mapped[BuyInStatus] = mapped_column(_enum_column(BuyInStatus, "buy_in_status"))
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by_telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.telegram_id")
    )


Index("ix_buy_ins_room_player_status", BuyInModel.room_player_id, BuyInModel.status)
