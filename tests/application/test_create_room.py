import pytest

from pokerman.application.use_cases.create_room import create_room
from pokerman.domain.enums import RoomStatus
from pokerman.domain.errors import RoomCodeExhaustedError
from tests.application.fakes import FakeRoomCodeGenerator, FakeUnitOfWork


class TestCreateRoom:
    async def test_creates_active_room_with_given_fields(self) -> None:
        uow = FakeUnitOfWork()
        codes = FakeRoomCodeGenerator(uow.db, codes=["4821"])

        room = await create_room(
            uow,
            codes,
            admin_telegram_id=1,
            admin_username="elnazar",
            admin_display_name="Elnazar",
            name="Poker Night #24",
            default_buy_in_amount=500,
            currency="KGS",
        )

        assert room.id is not None
        assert room.name == "Poker Night #24"
        assert str(room.code) == "4821"
        assert room.default_buy_in_amount == 500
        assert room.currency == "KGS"
        assert room.admin_telegram_id == 1
        assert room.status == RoomStatus.ACTIVE
        assert room.qr_file_id is None
        assert uow.committed is True

    async def test_assigns_a_non_empty_deep_link_token(self) -> None:
        uow = FakeUnitOfWork()
        codes = FakeRoomCodeGenerator(uow.db, codes=["1111"])

        room = await create_room(
            uow,
            codes,
            admin_telegram_id=1,
            admin_username=None,
            admin_display_name="Elnazar",
            name="Room",
            default_buy_in_amount=500,
            currency="KGS",
        )

        assert room.deep_link_token
        assert isinstance(room.deep_link_token, str)

    async def test_registers_the_admin_as_a_user(self) -> None:
        uow = FakeUnitOfWork()
        codes = FakeRoomCodeGenerator(uow.db, codes=["1111"])

        await create_room(
            uow,
            codes,
            admin_telegram_id=1,
            admin_username="elnazar",
            admin_display_name="Elnazar",
            name="Room",
            default_buy_in_amount=500,
            currency="KGS",
        )

        admin = await uow.users.get_by_telegram_id(1)
        assert admin is not None
        assert admin.display_name == "Elnazar"

    async def test_admin_is_auto_joined_as_a_room_player(self) -> None:
        uow = FakeUnitOfWork()
        codes = FakeRoomCodeGenerator(uow.db, codes=["1111"])

        room = await create_room(
            uow,
            codes,
            admin_telegram_id=1,
            admin_username="elnazar",
            admin_display_name="Elnazar",
            name="Room",
            default_buy_in_amount=500,
            currency="KGS",
        )

        assert room.id is not None
        member = await uow.room_players.get(room.id, 1)
        assert member is not None

    async def test_two_rooms_get_different_codes(self) -> None:
        uow = FakeUnitOfWork()
        codes = FakeRoomCodeGenerator(uow.db, codes=["1111", "2222"])

        first = await create_room(
            uow,
            codes,
            admin_telegram_id=1,
            admin_username=None,
            admin_display_name="A",
            name="Room A",
            default_buy_in_amount=500,
            currency="KGS",
        )
        second = await create_room(
            uow,
            codes,
            admin_telegram_id=2,
            admin_username=None,
            admin_display_name="B",
            name="Room B",
            default_buy_in_amount=500,
            currency="KGS",
        )

        assert first.code != second.code

    async def test_propagates_error_when_codes_are_exhausted(self) -> None:
        uow = FakeUnitOfWork()
        codes = FakeRoomCodeGenerator(uow.db, codes=["1111"])
        await create_room(
            uow,
            codes,
            admin_telegram_id=1,
            admin_username=None,
            admin_display_name="A",
            name="Room A",
            default_buy_in_amount=500,
            currency="KGS",
        )

        with pytest.raises(RoomCodeExhaustedError):
            await create_room(
                uow,
                codes,
                admin_telegram_id=2,
                admin_username=None,
                admin_display_name="B",
                name="Room B",
                default_buy_in_amount=500,
                currency="KGS",
            )
