from pokerman.application.use_cases.list_rooms_for_user import list_rooms_for_user
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestListRoomsForUser:
    async def test_includes_rooms_where_user_is_admin(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)

        rooms = await list_rooms_for_user(uow, telegram_id=1)

        assert [r.id for r in rooms] == [room.id]

    async def test_includes_rooms_where_user_is_a_player(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        rooms = await list_rooms_for_user(uow, telegram_id=2)

        assert [r.id for r in rooms] == [room.id]

    async def test_excludes_rooms_user_has_not_joined(self) -> None:
        uow = FakeUnitOfWork()
        await make_room(uow, admin_telegram_id=1)

        rooms = await list_rooms_for_user(uow, telegram_id=99)

        assert rooms == []

    async def test_lists_multiple_rooms_for_the_same_user(self) -> None:
        uow = FakeUnitOfWork()
        room_a = await make_room(uow, code="1111", admin_telegram_id=1, name="Room A")
        room_b = await make_room(uow, code="2222", admin_telegram_id=2, name="Room B")
        await add_player(uow, room_b, telegram_id=1, display_name="Elnazar")

        rooms = await list_rooms_for_user(uow, telegram_id=1)

        assert {r.id for r in rooms} == {room_a.id, room_b.id}
