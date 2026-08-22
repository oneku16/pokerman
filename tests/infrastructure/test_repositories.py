from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from pokerman.domain.entities import BuyIn, PokerRoom, RoomPlayer, User
from pokerman.domain.enums import BuyInStatus
from pokerman.domain.value_objects import RoomCode
from pokerman.infrastructure.db.repositories.buy_in_repository import SqlAlchemyBuyInRepository
from pokerman.infrastructure.db.repositories.room_player_repository import (
    SqlAlchemyRoomPlayerRepository,
)
from pokerman.infrastructure.db.repositories.room_repository import SqlAlchemyRoomRepository
from pokerman.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository

pytestmark = pytest.mark.integration

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _make_buy_in(*, room_player_id: int, amount: int = 500) -> BuyIn:
    return BuyIn.request(room_player_id=room_player_id, amount=amount, now=NOW)


async def _make_room(
    session: AsyncSession, *, code: str = "4821", admin_telegram_id: int = 1
) -> PokerRoom:
    await SqlAlchemyUserRepository(session).add(
        User.register(telegram_id=admin_telegram_id, username=None, display_name="Admin", now=NOW)
    )
    room = await SqlAlchemyRoomRepository(session).add(
        PokerRoom.open(
            name="Poker Night #24",
            code=RoomCode(code),
            deep_link_token=f"token-{code}",
            default_buy_in_amount=500,
            currency="KGS",
            admin_telegram_id=admin_telegram_id,
            now=NOW,
        )
    )
    await session.flush()
    return room


async def _make_member(session: AsyncSession, room: PokerRoom, telegram_id: int) -> RoomPlayer:
    assert room.id is not None
    users = SqlAlchemyUserRepository(session)
    if await users.get_by_telegram_id(telegram_id) is None:
        await users.add(
            User.register(telegram_id=telegram_id, username=None, display_name="Player", now=NOW)
        )
        await session.flush()
    member = await SqlAlchemyRoomPlayerRepository(session).add(
        RoomPlayer.join(room_id=room.id, user_telegram_id=telegram_id, now=NOW)
    )
    await session.flush()
    return member


class TestUserRepository:
    async def test_add_and_get_round_trip(self, session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(session)
        await repo.add(
            User.register(telegram_id=1, username="elnazar", display_name="Elnazar", now=NOW)
        )
        await session.flush()

        fetched = await repo.get_by_telegram_id(1)

        assert fetched is not None
        assert fetched.telegram_id == 1
        assert fetched.username == "elnazar"
        assert fetched.display_name == "Elnazar"

    async def test_get_unknown_returns_none(self, session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(session)

        assert await repo.get_by_telegram_id(404) is None

    async def test_save_persists_profile_updates(self, session: AsyncSession) -> None:
        repo = SqlAlchemyUserRepository(session)
        user = await repo.add(
            User.register(telegram_id=1, username="old", display_name="Old", now=NOW)
        )
        await session.flush()

        user.refresh_profile(username="new")
        await repo.save(user)
        await session.flush()
        session.expire_all()

        fetched = await repo.get_by_telegram_id(1)
        assert fetched is not None
        assert fetched.username == "new"
        assert fetched.display_name == "Old"


class TestRoomRepository:
    async def test_add_and_get_by_id_round_trip(self, session: AsyncSession) -> None:
        room = await _make_room(session)
        assert room.id is not None

        fetched = await SqlAlchemyRoomRepository(session).get_by_id(room.id)

        assert fetched is not None
        assert fetched.name == "Poker Night #24"
        assert str(fetched.code) == "4821"
        assert fetched.default_buy_in_amount == 500
        assert fetched.currency == "KGS"
        assert fetched.admin_telegram_id == 1

    async def test_get_by_code_finds_active_room(self, session: AsyncSession) -> None:
        room = await _make_room(session, code="1234")

        fetched = await SqlAlchemyRoomRepository(session).get_by_code(RoomCode("1234"))

        assert fetched is not None
        assert fetched.id == room.id

    async def test_get_by_code_ignores_closed_rooms(self, session: AsyncSession) -> None:
        room = await _make_room(session, code="1234")
        room.close(NOW)
        await SqlAlchemyRoomRepository(session).save(room)
        await session.flush()

        fetched = await SqlAlchemyRoomRepository(session).get_by_code(RoomCode("1234"))

        assert fetched is None

    async def test_get_by_deep_link_token_finds_room_regardless_of_status(
        self, session: AsyncSession
    ) -> None:
        room = await _make_room(session, code="1234")
        room.close(NOW)
        await SqlAlchemyRoomRepository(session).save(room)
        await session.flush()

        fetched = await SqlAlchemyRoomRepository(session).get_by_deep_link_token(
            room.deep_link_token
        )

        assert fetched is not None
        assert fetched.id == room.id

    async def test_is_code_taken_by_active_room(self, session: AsyncSession) -> None:
        await _make_room(session, code="1234")
        repo = SqlAlchemyRoomRepository(session)

        assert await repo.is_code_taken_by_active_room(RoomCode("1234")) is True
        assert await repo.is_code_taken_by_active_room(RoomCode("9999")) is False

    async def test_save_persists_close(self, session: AsyncSession) -> None:
        room = await _make_room(session)
        assert room.id is not None
        repo = SqlAlchemyRoomRepository(session)

        room.close(NOW)
        await repo.save(room)
        await session.flush()
        session.expire_all()

        fetched = await repo.get_by_id(room.id)
        assert fetched is not None
        assert fetched.closed_at == NOW

    async def test_list_for_user_includes_admin_and_member_rooms(
        self, session: AsyncSession
    ) -> None:
        admin_room = await _make_room(session, code="1111", admin_telegram_id=1)
        await _make_member(session, admin_room, telegram_id=1)
        other_room = await _make_room(session, code="2222", admin_telegram_id=2)
        await _make_member(session, other_room, telegram_id=1)

        rooms = await SqlAlchemyRoomRepository(session).list_for_user(1)

        assert {r.id for r in rooms} == {admin_room.id, other_room.id}

    async def test_active_code_uniqueness_is_enforced_by_the_database(
        self, session: AsyncSession
    ) -> None:
        await _make_room(session, code="1234", admin_telegram_id=1)
        await SqlAlchemyUserRepository(session).add(
            User.register(telegram_id=2, username=None, display_name="Admin2", now=NOW)
        )

        with pytest.raises(IntegrityError):
            await SqlAlchemyRoomRepository(session).add(
                PokerRoom.open(
                    name="Duplicate Code Room",
                    code=RoomCode("1234"),
                    deep_link_token="other-token",
                    default_buy_in_amount=500,
                    currency="KGS",
                    admin_telegram_id=2,
                    now=NOW,
                )
            )

    async def test_closed_rooms_free_their_code_for_reuse(self, session: AsyncSession) -> None:
        first = await _make_room(session, code="1234", admin_telegram_id=1)
        first.close(NOW)
        await SqlAlchemyRoomRepository(session).save(first)
        await session.flush()

        await SqlAlchemyUserRepository(session).add(
            User.register(telegram_id=2, username=None, display_name="Admin2", now=NOW)
        )
        second = await SqlAlchemyRoomRepository(session).add(
            PokerRoom.open(
                name="Reused Code Room",
                code=RoomCode("1234"),
                deep_link_token="another-token",
                default_buy_in_amount=500,
                currency="KGS",
                admin_telegram_id=2,
                now=NOW,
            )
        )
        await session.flush()

        assert second.id is not None


class TestRoomPlayerRepository:
    async def test_add_and_get_round_trip(self, session: AsyncSession) -> None:
        room = await _make_room(session)
        assert room.id is not None
        member = await _make_member(session, room, telegram_id=2)

        fetched = await SqlAlchemyRoomPlayerRepository(session).get(room.id, 2)

        assert fetched is not None
        assert fetched.id == member.id

    async def test_get_returns_none_for_non_member(self, session: AsyncSession) -> None:
        room = await _make_room(session)
        assert room.id is not None

        fetched = await SqlAlchemyRoomPlayerRepository(session).get(room.id, 99)

        assert fetched is None

    async def test_list_for_room(self, session: AsyncSession) -> None:
        room = await _make_room(session, admin_telegram_id=1)
        assert room.id is not None
        await _make_member(session, room, telegram_id=2)
        await _make_member(session, room, telegram_id=3)

        members = await SqlAlchemyRoomPlayerRepository(session).list_for_room(room.id)

        assert {m.user_telegram_id for m in members} == {2, 3}

    async def test_duplicate_membership_is_enforced_by_the_database(
        self, session: AsyncSession
    ) -> None:
        room = await _make_room(session, admin_telegram_id=1)
        assert room.id is not None
        await _make_member(session, room, telegram_id=2)

        with pytest.raises(IntegrityError):
            await SqlAlchemyRoomPlayerRepository(session).add(
                RoomPlayer.join(room_id=room.id, user_telegram_id=2, now=NOW)
            )

    async def test_save_persists_cash_out(self, session: AsyncSession) -> None:
        room = await _make_room(session, admin_telegram_id=1)
        assert room.id is not None
        repo = SqlAlchemyRoomPlayerRepository(session)
        member = await _make_member(session, room, telegram_id=2)
        assert member.id is not None

        member.record_cash_out(1200, NOW)
        await repo.save(member)
        await session.flush()
        session.expire_all()

        fetched = await repo.get_by_id(member.id)
        assert fetched is not None
        assert fetched.final_chip_count == 1200
        assert fetched.cashed_out_at == NOW


class TestBuyInRepository:
    async def test_add_and_get_round_trip(self, session: AsyncSession) -> None:
        room = await _make_room(session, admin_telegram_id=1)
        member = await _make_member(session, room, telegram_id=2)
        assert member.id is not None
        repo = SqlAlchemyBuyInRepository(session)

        buy_in = await repo.add(_make_buy_in(room_player_id=member.id))
        await session.flush()
        assert buy_in.id is not None

        fetched = await repo.get_by_id(buy_in.id)
        assert fetched is not None
        assert fetched.amount == 500
        assert fetched.status == BuyInStatus.PENDING

    async def test_save_persists_confirmation(self, session: AsyncSession) -> None:
        room = await _make_room(session, admin_telegram_id=1)
        member = await _make_member(session, room, telegram_id=2)
        assert member.id is not None
        repo = SqlAlchemyBuyInRepository(session)
        buy_in = await repo.add(_make_buy_in(room_player_id=member.id))
        await session.flush()
        assert buy_in.id is not None

        buy_in.confirm(decided_by_telegram_id=1, now=NOW)
        await repo.save(buy_in)
        await session.flush()
        session.expire_all()

        fetched = await repo.get_by_id(buy_in.id)
        assert fetched is not None
        assert fetched.status == BuyInStatus.CONFIRMED
        assert fetched.decided_by_telegram_id == 1

    async def test_list_pending_for_room_filters_by_status_and_room(
        self, session: AsyncSession
    ) -> None:
        room_a = await _make_room(session, code="1111", admin_telegram_id=1)
        assert room_a.id is not None
        room_b = await _make_room(session, code="2222", admin_telegram_id=3)
        member_a = await _make_member(session, room_a, telegram_id=2)
        member_b = await _make_member(session, room_b, telegram_id=4)
        assert member_a.id is not None
        assert member_b.id is not None
        repo = SqlAlchemyBuyInRepository(session)

        pending_a = await repo.add(_make_buy_in(room_player_id=member_a.id))
        confirmed_a = await repo.add(_make_buy_in(room_player_id=member_a.id))
        await repo.add(_make_buy_in(room_player_id=member_b.id))
        await session.flush()
        confirmed_a.confirm(decided_by_telegram_id=1, now=NOW)
        await repo.save(confirmed_a)
        await session.flush()

        pending = await repo.list_pending_for_room(room_a.id)

        assert [b.id for b in pending] == [pending_a.id]

    async def test_list_for_room_player_returns_all_statuses(self, session: AsyncSession) -> None:
        room = await _make_room(session, admin_telegram_id=1)
        member = await _make_member(session, room, telegram_id=2)
        assert member.id is not None
        repo = SqlAlchemyBuyInRepository(session)
        first = await repo.add(_make_buy_in(room_player_id=member.id))
        second = await repo.add(_make_buy_in(room_player_id=member.id))
        await session.flush()
        second.reject(decided_by_telegram_id=1, now=NOW)
        await repo.save(second)
        await session.flush()

        history = await repo.list_for_room_player(member.id)

        assert {b.id for b in history} == {first.id, second.id}
