from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pokerman.domain.entities import BuyIn, PokerRoom, RoomPlayer, User
from pokerman.domain.value_objects import RoomCode
from pokerman.infrastructure.db.player_statistics_query import SqlAlchemyPlayerStatisticsQuery
from pokerman.infrastructure.db.repositories.buy_in_repository import SqlAlchemyBuyInRepository
from pokerman.infrastructure.db.repositories.room_player_repository import (
    SqlAlchemyRoomPlayerRepository,
)
from pokerman.infrastructure.db.repositories.room_repository import SqlAlchemyRoomRepository
from pokerman.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository

pytestmark = pytest.mark.integration

NOW = datetime(2026, 1, 1, tzinfo=UTC)


async def _make_room(
    session: AsyncSession, *, code: str, admin_telegram_id: int
) -> PokerRoom:
    rooms = SqlAlchemyRoomRepository(session)
    users = SqlAlchemyUserRepository(session)
    if await users.get_by_telegram_id(admin_telegram_id) is None:
        await users.add(
            User.register(
                telegram_id=admin_telegram_id, username=None, display_name="Admin", now=NOW
            )
        )
    room = await rooms.add(
        PokerRoom.open(
            name=f"Room {code}",
            code=RoomCode(code),
            deep_link_token=f"tok-{code}",
            default_buy_in_amount=500,
            currency="KGS",
            admin_telegram_id=admin_telegram_id,
            now=NOW,
        )
    )
    await session.flush()
    return room


async def _add_member(session: AsyncSession, room: PokerRoom, telegram_id: int) -> RoomPlayer:
    assert room.id is not None
    users = SqlAlchemyUserRepository(session)
    if await users.get_by_telegram_id(telegram_id) is None:
        await users.add(
            User.register(telegram_id=telegram_id, username=None, display_name="Azamat", now=NOW)
        )
        await session.flush()
    member = await SqlAlchemyRoomPlayerRepository(session).add(
        RoomPlayer.join(room_id=room.id, user_telegram_id=telegram_id, now=NOW)
    )
    await session.flush()
    return member


async def _confirmed_buy_in(session: AsyncSession, room_player_id: int, amount: int) -> BuyIn:
    buy_ins = SqlAlchemyBuyInRepository(session)
    buy_in = await buy_ins.add(
        BuyIn.request(room_player_id=room_player_id, amount=amount, now=NOW)
    )
    await session.flush()
    buy_in.confirm(decided_by_telegram_id=1, now=NOW)
    await buy_ins.save(buy_in)
    await session.flush()
    return buy_in


class TestPlayerStatisticsQuery:
    async def test_zero_stats_for_unknown_player(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        stats = await SqlAlchemyPlayerStatisticsQuery(session_factory).get_statistics(999)

        assert stats.games_played == 0
        assert stats.total_spent == 0
        assert stats.total_cashed_out == 0
        assert stats.net_result == 0

    async def test_open_room_membership_does_not_count_as_played(
        self, session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        room = await _make_room(session, code="1111", admin_telegram_id=1)
        member = await _add_member(session, room, telegram_id=2)
        assert member.id is not None
        await _confirmed_buy_in(session, member.id, 500)
        await session.commit()

        stats = await SqlAlchemyPlayerStatisticsQuery(session_factory).get_statistics(2)

        assert stats.games_played == 0
        assert stats.total_spent == 500

    async def test_aggregates_across_closed_rooms_only_summing_net_where_cashed_out(
        self, session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        room_a = await _make_room(session, code="1111", admin_telegram_id=1)
        member_a = await _add_member(session, room_a, telegram_id=2)
        assert member_a.id is not None
        assert room_a.id is not None
        await _confirmed_buy_in(session, member_a.id, 500)
        room_a.close(NOW)
        await SqlAlchemyRoomRepository(session).save(room_a)
        member_a.record_cash_out(800, NOW)
        await SqlAlchemyRoomPlayerRepository(session).save(member_a)

        room_b = await _make_room(session, code="2222", admin_telegram_id=1)
        member_b = await _add_member(session, room_b, telegram_id=2)
        assert member_b.id is not None
        assert room_b.id is not None
        await _confirmed_buy_in(session, member_b.id, 300)
        room_b.close(NOW)
        await SqlAlchemyRoomRepository(session).save(room_b)
        # no cash-out recorded for room_b

        await session.commit()

        stats = await SqlAlchemyPlayerStatisticsQuery(session_factory).get_statistics(2)

        assert stats.games_played == 2
        assert stats.total_spent == 800
        assert stats.total_buy_in_count == 2
        assert stats.total_cashed_out == 800
        assert stats.net_result == 300
        assert stats.display_name == "Azamat"
