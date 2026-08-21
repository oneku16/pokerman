import pytest

from pokerman.application.use_cases.get_room import get_room
from pokerman.domain.errors import RoomNotFoundError
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import make_room


class TestGetRoom:
    async def test_returns_the_room(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None

        fetched = await get_room(uow, room_id=room.id)

        assert fetched.id == room.id
        assert fetched.name == room.name

    async def test_unknown_room_raises_not_found(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(RoomNotFoundError):
            await get_room(uow, room_id=404)
