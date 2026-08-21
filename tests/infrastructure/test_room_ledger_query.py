from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pokerman.domain.entities import BuyIn, PokerRoom, RoomPlayer, User
from pokerman.domain.value_objects import RoomCode
from pokerman.infrastructure.db.repositories.buy_in_repository import SqlAlchemyBuyInRepository
from pokerman.infrastructure.db.repositories.room_player_repository import (
    SqlAlchemyRoomPlayerRepository,
)
from pokerman.infrastructure.db.repositories.room_repository import SqlAlchemyRoomRepository
from pokerman.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository
from pokerman.infrastructure.db.room_ledger_query import SqlAlchemyRoomLedgerQuery

pytestmark = pytest.mark.integration

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _first_buy_in(*, room_player_id: int, amount: int = 500) -> BuyIn:
    return BuyIn.request(
        room_player_id=room_player_id,
        amount=amount,
        is_first_buy_in=True,
        default_amount=500,
        now=NOW,
    )


class TestRoomLedgerQuery:
    async def test_player_totals_only_count_confirmed_buy_ins(
        self, session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        users = SqlAlchemyUserRepository(session)
        rooms = SqlAlchemyRoomRepository(session)
        room_players = SqlAlchemyRoomPlayerRepository(session)
        buy_ins = SqlAlchemyBuyInRepository(session)

        await users.add(
            User.register(telegram_id=1, username=None, display_name="Elnazar", now=NOW)
        )
        await users.add(User.register(telegram_id=2, username=None, display_name="Azamat", now=NOW))
        room = await rooms.add(
            PokerRoom.open(
                name="Poker Night #24",
                code=RoomCode("4821"),
                deep_link_token="tok",
                default_buy_in_amount=500,
                currency="KGS",
                admin_telegram_id=1,
                now=NOW,
            )
        )
        await session.flush()
        assert room.id is not None

        admin_member = await room_players.add(
            RoomPlayer.join(room_id=room.id, user_telegram_id=1, now=NOW)
        )
        azamat_member = await room_players.add(
            RoomPlayer.join(room_id=room.id, user_telegram_id=2, now=NOW)
        )
        await session.flush()
        assert admin_member.id is not None
        assert azamat_member.id is not None

        confirmed_1 = await buy_ins.add(
            _first_buy_in(room_player_id=azamat_member.id)
        )
        confirmed_2 = await buy_ins.add(
            _first_buy_in(room_player_id=azamat_member.id)
        )
        await buy_ins.add(_first_buy_in(room_player_id=azamat_member.id))
        rejected = await buy_ins.add(
            _first_buy_in(room_player_id=azamat_member.id)
        )
        await session.flush()
        confirmed_1.confirm(decided_by_telegram_id=1, now=NOW)
        confirmed_2.confirm(decided_by_telegram_id=1, now=NOW)
        rejected.reject(decided_by_telegram_id=1, now=NOW)
        await buy_ins.save(confirmed_1)
        await buy_ins.save(confirmed_2)
        await buy_ins.save(rejected)
        await session.commit()

        rows = await SqlAlchemyRoomLedgerQuery(session_factory).player_totals(room.id)

        by_telegram_id = {row.user_telegram_id: row for row in rows}
        assert by_telegram_id[2].confirmed_total == 1000
        assert by_telegram_id[2].confirmed_count == 2
        assert by_telegram_id[2].display_name == "Azamat"
        assert by_telegram_id[1].confirmed_total == 0
        assert by_telegram_id[1].confirmed_count == 0

    async def test_player_with_no_buy_ins_still_appears(
        self, session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        users = SqlAlchemyUserRepository(session)
        rooms = SqlAlchemyRoomRepository(session)
        room_players = SqlAlchemyRoomPlayerRepository(session)

        await users.add(
            User.register(telegram_id=1, username=None, display_name="Elnazar", now=NOW)
        )
        room = await rooms.add(
            PokerRoom.open(
                name="Poker Night #24",
                code=RoomCode("4821"),
                deep_link_token="tok",
                default_buy_in_amount=500,
                currency="KGS",
                admin_telegram_id=1,
                now=NOW,
            )
        )
        await session.flush()
        assert room.id is not None
        await room_players.add(RoomPlayer.join(room_id=room.id, user_telegram_id=1, now=NOW))
        await session.commit()

        rows = await SqlAlchemyRoomLedgerQuery(session_factory).player_totals(room.id)

        assert len(rows) == 1
        assert rows[0].confirmed_total == 0
        assert rows[0].confirmed_count == 0
