from dataclasses import dataclass

from pokerman.application.ports import UnitOfWork
from pokerman.domain.entities import BuyIn, PokerRoom, RoomPlayer
from pokerman.domain.errors import BuyInNotFoundError, RoomNotFoundError


@dataclass(frozen=True, slots=True)
class BuyInDecision:
    buy_in: BuyIn
    room: PokerRoom
    player_telegram_id: int


async def get_buy_in_room_and_member(
    uow: UnitOfWork, buy_in_id: int
) -> tuple[BuyIn, PokerRoom, RoomPlayer]:
    buy_in = await uow.buy_ins.get_by_id(buy_in_id)
    if buy_in is None:
        raise BuyInNotFoundError(f"buy-in {buy_in_id} not found")

    member = await uow.room_players.get_by_id(buy_in.room_player_id)
    if member is None:
        raise RoomNotFoundError(f"room membership for buy-in {buy_in_id} not found")

    room = await uow.rooms.get_by_id(member.room_id)
    if room is None:
        raise RoomNotFoundError(f"room for buy-in {buy_in_id} not found")

    return buy_in, room, member
