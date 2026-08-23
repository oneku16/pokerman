from __future__ import annotations

import itertools
from types import TracebackType

from pokerman.application.read_models import PlayerLedgerRow, PlayerStatistics
from pokerman.domain.entities import BuyIn, PokerRoom, RoomPlayer, User
from pokerman.domain.enums import BuyInStatus, RoomStatus
from pokerman.domain.errors import RoomCodeExhaustedError
from pokerman.domain.value_objects import RoomCode


class FakeDatabase:
    def __init__(self) -> None:
        self.users: dict[int, User] = {}
        self.rooms: dict[int, PokerRoom] = {}
        self.room_players: dict[int, RoomPlayer] = {}
        self.buy_ins: dict[int, BuyIn] = {}
        self.room_id_seq = itertools.count(1)
        self.room_player_id_seq = itertools.count(1)
        self.buy_in_id_seq = itertools.count(1)


class FakeUserRepository:
    def __init__(self, db: FakeDatabase) -> None:
        self._db = db

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return self._db.users.get(telegram_id)

    async def add(self, user: User) -> User:
        self._db.users[user.telegram_id] = user
        return user

    async def save(self, user: User) -> None:
        self._db.users[user.telegram_id] = user


class FakeRoomRepository:
    def __init__(self, db: FakeDatabase) -> None:
        self._db = db

    async def add(self, room: PokerRoom) -> PokerRoom:
        room.id = next(self._db.room_id_seq)
        self._db.rooms[room.id] = room
        return room

    async def get_by_id(self, room_id: int) -> PokerRoom | None:
        return self._db.rooms.get(room_id)

    async def get_by_code(self, code: RoomCode) -> PokerRoom | None:
        for room in self._db.rooms.values():
            if room.code == code and room.status == RoomStatus.ACTIVE:
                return room
        return None

    async def get_by_deep_link_token(self, token: str) -> PokerRoom | None:
        for room in self._db.rooms.values():
            if room.deep_link_token == token:
                return room
        return None

    async def is_code_taken_by_active_room(self, code: RoomCode) -> bool:
        return any(
            room.code == code and room.status == RoomStatus.ACTIVE
            for room in self._db.rooms.values()
        )

    async def save(self, room: PokerRoom) -> None:
        assert room.id is not None
        self._db.rooms[room.id] = room

    async def list_for_user(
        self, telegram_id: int, *, limit: int | None = None
    ) -> list[PokerRoom]:
        memberships = sorted(
            (rp for rp in self._db.room_players.values() if rp.user_telegram_id == telegram_id),
            key=lambda rp: rp.joined_at,
            reverse=True,
        )
        rooms = [self._db.rooms[rp.room_id] for rp in memberships if rp.room_id in self._db.rooms]
        return rooms if limit is None else rooms[:limit]


class FakeRoomPlayerRepository:
    def __init__(self, db: FakeDatabase) -> None:
        self._db = db

    async def add(self, member: RoomPlayer) -> RoomPlayer:
        member.id = next(self._db.room_player_id_seq)
        self._db.room_players[member.id] = member
        return member

    async def get(self, room_id: int, user_telegram_id: int) -> RoomPlayer | None:
        for rp in self._db.room_players.values():
            if rp.room_id == room_id and rp.user_telegram_id == user_telegram_id:
                return rp
        return None

    async def get_by_id(self, room_player_id: int) -> RoomPlayer | None:
        return self._db.room_players.get(room_player_id)

    async def list_for_room(self, room_id: int) -> list[RoomPlayer]:
        return [rp for rp in self._db.room_players.values() if rp.room_id == room_id]

    async def save(self, member: RoomPlayer) -> None:
        assert member.id is not None
        self._db.room_players[member.id] = member


class FakeBuyInRepository:
    def __init__(self, db: FakeDatabase) -> None:
        self._db = db

    async def add(self, buy_in: BuyIn) -> BuyIn:
        buy_in.id = next(self._db.buy_in_id_seq)
        self._db.buy_ins[buy_in.id] = buy_in
        return buy_in

    async def get_by_id(self, buy_in_id: int) -> BuyIn | None:
        return self._db.buy_ins.get(buy_in_id)

    async def save(self, buy_in: BuyIn) -> None:
        assert buy_in.id is not None
        self._db.buy_ins[buy_in.id] = buy_in

    async def list_pending_for_room(self, room_id: int) -> list[BuyIn]:
        room_player_ids = {rp.id for rp in self._db.room_players.values() if rp.room_id == room_id}
        return [
            b
            for b in self._db.buy_ins.values()
            if b.room_player_id in room_player_ids and b.status == BuyInStatus.PENDING
        ]

    async def list_for_room_player(self, room_player_id: int) -> list[BuyIn]:
        return [b for b in self._db.buy_ins.values() if b.room_player_id == room_player_id]


class FakeRoomCodeGenerator:
    def __init__(self, db: FakeDatabase, codes: list[str] | None = None) -> None:
        self._db = db
        self._preset_codes = list(codes) if codes is not None else None

    async def generate_unique_code(self) -> RoomCode:
        candidates = (
            (RoomCode(value) for value in self._preset_codes)
            if self._preset_codes is not None
            else (RoomCode.generate() for _ in range(20))
        )
        for code in candidates:
            if not await self._is_taken(code):
                return code
        raise RoomCodeExhaustedError("could not find a free room code")

    async def _is_taken(self, code: RoomCode) -> bool:
        return any(
            room.code == code and room.status == RoomStatus.ACTIVE
            for room in self._db.rooms.values()
        )


class FakeRoomLedgerQuery:
    def __init__(self, db: FakeDatabase) -> None:
        self._db = db

    async def player_totals(self, room_id: int) -> list[PlayerLedgerRow]:
        rows: list[PlayerLedgerRow] = []
        for member in self._db.room_players.values():
            if member.room_id != room_id:
                continue
            assert member.id is not None
            confirmed = [
                b
                for b in self._db.buy_ins.values()
                if b.room_player_id == member.id and b.status == BuyInStatus.CONFIRMED
            ]
            user = self._db.users.get(member.user_telegram_id)
            display_name = user.display_name if user is not None else str(member.user_telegram_id)
            rows.append(
                PlayerLedgerRow(
                    room_player_id=member.id,
                    user_telegram_id=member.user_telegram_id,
                    display_name=display_name,
                    confirmed_total=sum(b.amount for b in confirmed),
                    confirmed_count=len(confirmed),
                )
            )
        return rows


class FakePlayerStatisticsQuery:
    def __init__(self, db: FakeDatabase) -> None:
        self._db = db

    async def get_statistics(self, telegram_id: int) -> PlayerStatistics:
        members = [
            rp for rp in self._db.room_players.values() if rp.user_telegram_id == telegram_id
        ]
        games_played = len(
            {
                rp.room_id
                for rp in members
                if self._db.rooms.get(rp.room_id) is not None
                and self._db.rooms[rp.room_id].status == RoomStatus.CLOSED
            }
        )

        confirmed_by_room_player: dict[int, int] = {}
        for buy_in in self._db.buy_ins.values():
            if buy_in.status == BuyInStatus.CONFIRMED:
                confirmed_by_room_player[buy_in.room_player_id] = (
                    confirmed_by_room_player.get(buy_in.room_player_id, 0) + buy_in.amount
                )

        total_spent = 0
        total_buy_in_count = 0
        for member in members:
            assert member.id is not None
            total_spent += confirmed_by_room_player.get(member.id, 0)
            total_buy_in_count += sum(
                1
                for b in self._db.buy_ins.values()
                if b.room_player_id == member.id and b.status == BuyInStatus.CONFIRMED
            )

        total_cashed_out = 0
        net_result = 0
        for member in members:
            if member.final_chip_count is None:
                continue
            assert member.id is not None
            spent_here = confirmed_by_room_player.get(member.id, 0)
            total_cashed_out += member.final_chip_count
            net_result += member.final_chip_count - spent_here

        user = self._db.users.get(telegram_id)
        display_name = user.display_name if user is not None else str(telegram_id)

        return PlayerStatistics(
            telegram_id=telegram_id,
            display_name=display_name,
            games_played=games_played,
            total_buy_in_count=total_buy_in_count,
            total_spent=total_spent,
            total_cashed_out=total_cashed_out,
            net_result=net_result,
        )


class FakeUnitOfWork:
    def __init__(self, db: FakeDatabase | None = None) -> None:
        self.db = db if db is not None else FakeDatabase()
        self.users = FakeUserRepository(self.db)
        self.rooms = FakeRoomRepository(self.db)
        self.room_players = FakeRoomPlayerRepository(self.db)
        self.buy_ins = FakeBuyInRepository(self.db)
        self.committed = False

    async def __aenter__(self) -> FakeUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass
