from dataclasses import dataclass

from pokerman.application.ports import RoomLedgerQuery, UnitOfWork
from pokerman.application.read_models import PlayerLedgerRow
from pokerman.domain.entities import PokerRoom
from pokerman.domain.errors import NotRoomMemberError, RoomNotFoundError


@dataclass(frozen=True, slots=True)
class RoomDashboard:
    room: PokerRoom
    players: list[PlayerLedgerRow]

    @property
    def total_confirmed(self) -> int:
        return sum(row.confirmed_total for row in self.players)


async def get_room_dashboard(
    uow: UnitOfWork,
    ledger: RoomLedgerQuery,
    *,
    room_id: int,
    requesting_telegram_id: int,
) -> RoomDashboard:
    async with uow:
        room = await uow.rooms.get_by_id(room_id)
        if room is None:
            raise RoomNotFoundError(f"room {room_id} not found")

        if requesting_telegram_id != room.admin_telegram_id:
            member = await uow.room_players.get(room_id, requesting_telegram_id)
            if member is None:
                raise NotRoomMemberError(
                    f"user {requesting_telegram_id} is not a member of room {room_id}"
                )

        players = await ledger.player_totals(room_id)
        return RoomDashboard(room=room, players=players)
