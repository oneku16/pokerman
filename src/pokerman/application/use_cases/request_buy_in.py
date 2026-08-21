from dataclasses import dataclass
from datetime import UTC, datetime

from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import BuyIn, PokerRoom
from pokerman.domain.errors import NotRoomMemberError, RoomNotFoundError


@dataclass(frozen=True, slots=True)
class BuyInRequest:
    buy_in: BuyIn
    room: PokerRoom


async def request_buy_in(
    uow: UnitOfWork,
    *,
    room_id: int,
    player_telegram_id: int,
    amount: int | None = None,
) -> BuyInRequest:
    async with uow:
        room = await uow.rooms.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundError(f"room {room_id} not found")
        room.ensure_active()

        member = await uow.room_players.get(room_id, player_telegram_id)
        if member is None:
            raise NotRoomMemberError(f"user {player_telegram_id} has not joined room {room_id}")
        assert member.id is not None

        buy_in = await uow.buy_ins.add(
            BuyIn.request(
                room_player_id=member.id,
                amount=amount if amount is not None else room.default_buy_in_amount,
                now=datetime.now(UTC),
            )
        )
        await uow.commit()
        return BuyInRequest(buy_in=buy_in, room=room)
