from dataclasses import dataclass

from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import BuyIn, PokerRoom
from pokerman.domain.enums import BuyInStatus
from pokerman.domain.errors import NotRoomMemberError, RoomNotFoundError, UnauthorizedActionError


@dataclass(frozen=True, slots=True)
class PlayerHistory:
    room: PokerRoom
    buy_ins: list[BuyIn]

    @property
    def confirmed_total(self) -> int:
        return sum(b.amount for b in self.buy_ins if b.status == BuyInStatus.CONFIRMED)


async def get_player_history(
    uow: UnitOfWork,
    *,
    room_id: int,
    target_telegram_id: int,
    requesting_telegram_id: int,
) -> PlayerHistory:
    async with uow:
        room = await uow.rooms.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundError(f"room {room_id} not found")

        if requesting_telegram_id not in (target_telegram_id, room.admin_telegram_id):
            raise UnauthorizedActionError(
                f"user {requesting_telegram_id} cannot view history for {target_telegram_id}"
            )

        member = await uow.room_players.get(room_id, target_telegram_id)
        if member is None:
            raise NotRoomMemberError(f"user {target_telegram_id} is not a member of room {room_id}")
        assert member.id is not None

        buy_ins = await uow.buy_ins.list_for_room_player(member.id)
        return PlayerHistory(room=room, buy_ins=buy_ins)
