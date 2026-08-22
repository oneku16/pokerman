from pokerman.application.use_cases.list_room_members import list_room_members
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestListRoomMembers:
    async def test_lists_admin_and_players(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await add_player(uow, room, telegram_id=3, display_name="Nursultan")

        members = await list_room_members(uow, room_id=room.id)

        assert {m.user_telegram_id for m in members} == {1, 2, 3}

    async def test_empty_for_unknown_room(self) -> None:
        uow = FakeUnitOfWork()

        members = await list_room_members(uow, room_id=404)

        assert members == []
