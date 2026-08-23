from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.get_current_or_last_room import get_current_or_last_room
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import make_room


class TestGetCurrentOrLastRoom:
    async def test_returns_none_when_user_has_no_rooms(self) -> None:
        uow = FakeUnitOfWork()

        room = await get_current_or_last_room(uow, telegram_id=1)

        assert room is None

    async def test_prefers_the_active_room_over_a_more_recently_joined_closed_room(self) -> None:
        uow = FakeUnitOfWork()
        active_room = await make_room(uow, code="1111", admin_telegram_id=1, name="Active")
        closed_room = await make_room(uow, code="2222", admin_telegram_id=1, name="Closed")
        assert closed_room.id is not None
        await close_room(uow, room_id=closed_room.id, admin_telegram_id=1)

        room = await get_current_or_last_room(uow, telegram_id=1)

        assert room is not None
        assert room.id == active_room.id

    async def test_falls_back_to_the_most_recently_joined_closed_room(self) -> None:
        uow = FakeUnitOfWork()
        older_closed = await make_room(uow, code="1111", admin_telegram_id=1, name="Older")
        newer_closed = await make_room(uow, code="2222", admin_telegram_id=1, name="Newer")
        assert older_closed.id is not None
        assert newer_closed.id is not None
        await close_room(uow, room_id=older_closed.id, admin_telegram_id=1)
        await close_room(uow, room_id=newer_closed.id, admin_telegram_id=1)

        room = await get_current_or_last_room(uow, telegram_id=1)

        assert room is not None
        assert room.id == newer_closed.id
