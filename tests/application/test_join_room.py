import pytest

from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.create_room import create_room
from pokerman.application.use_cases.join_room import join_room_by_code, join_room_by_deep_link
from pokerman.domain.entities import PokerRoom
from pokerman.domain.errors import DuplicateMembershipError, RoomClosedError, RoomNotFoundError
from tests.application.fakes import FakeRoomCodeGenerator, FakeUnitOfWork


async def _create_room(uow: FakeUnitOfWork, code: str = "4821") -> PokerRoom:
    codes = FakeRoomCodeGenerator(uow.db, codes=[code])
    return await create_room(
        uow,
        codes,
        admin_telegram_id=1,
        admin_username="elnazar",
        admin_display_name="Elnazar",
        name="Poker Night #24",
        default_buy_in_amount=500,
        currency="KGS",
    )


class TestJoinRoomByCode:
    async def test_new_player_joins_successfully(self) -> None:
        uow = FakeUnitOfWork()
        room = await _create_room(uow)
        assert room.id is not None

        joined = await join_room_by_code(
            uow, code="4821", telegram_id=2, username="azamat", display_name="Azamat"
        )

        assert joined.id == room.id
        member = await uow.room_players.get(room.id, 2)
        assert member is not None

    async def test_registers_the_joining_user(self) -> None:
        uow = FakeUnitOfWork()
        await _create_room(uow)

        await join_room_by_code(
            uow, code="4821", telegram_id=2, username="azamat", display_name="Azamat"
        )

        user = await uow.users.get_by_telegram_id(2)
        assert user is not None
        assert user.display_name == "Azamat"

    async def test_unknown_code_raises_not_found(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(RoomNotFoundError):
            await join_room_by_code(
                uow, code="9999", telegram_id=2, username=None, display_name="Azamat"
            )

    async def test_duplicate_join_is_rejected(self) -> None:
        uow = FakeUnitOfWork()
        await _create_room(uow)
        await join_room_by_code(
            uow, code="4821", telegram_id=2, username=None, display_name="Azamat"
        )

        with pytest.raises(DuplicateMembershipError):
            await join_room_by_code(
                uow, code="4821", telegram_id=2, username=None, display_name="Azamat"
            )

    async def test_admin_rejoining_own_room_is_rejected(self) -> None:
        uow = FakeUnitOfWork()
        await _create_room(uow)

        with pytest.raises(DuplicateMembershipError):
            await join_room_by_code(
                uow, code="4821", telegram_id=1, username=None, display_name="Elnazar"
            )

    async def test_closed_rooms_code_is_no_longer_found(self) -> None:
        uow = FakeUnitOfWork()
        room = await _create_room(uow)
        assert room.id is not None
        await close_room(uow, room_id=room.id, admin_telegram_id=1)

        with pytest.raises(RoomNotFoundError):
            await join_room_by_code(
                uow, code="4821", telegram_id=2, username=None, display_name="Azamat"
            )


class TestJoinRoomByDeepLink:
    async def test_new_player_joins_successfully(self) -> None:
        uow = FakeUnitOfWork()
        room = await _create_room(uow)

        joined = await join_room_by_deep_link(
            uow,
            token=room.deep_link_token,
            telegram_id=2,
            username="azamat",
            display_name="Azamat",
        )

        assert joined.id == room.id

    async def test_unknown_token_raises_not_found(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(RoomNotFoundError):
            await join_room_by_deep_link(
                uow, token="does-not-exist", telegram_id=2, username=None, display_name="Azamat"
            )

    async def test_duplicate_join_is_rejected(self) -> None:
        uow = FakeUnitOfWork()
        room = await _create_room(uow)
        await join_room_by_deep_link(
            uow, token=room.deep_link_token, telegram_id=2, username=None, display_name="Azamat"
        )

        with pytest.raises(DuplicateMembershipError):
            await join_room_by_deep_link(
                uow,
                token=room.deep_link_token,
                telegram_id=2,
                username=None,
                display_name="Azamat",
            )

    async def test_cannot_join_a_closed_room(self) -> None:
        uow = FakeUnitOfWork()
        room = await _create_room(uow)
        assert room.id is not None
        await close_room(uow, room_id=room.id, admin_telegram_id=1)

        with pytest.raises(RoomClosedError):
            await join_room_by_deep_link(
                uow,
                token=room.deep_link_token,
                telegram_id=2,
                username=None,
                display_name="Azamat",
            )
