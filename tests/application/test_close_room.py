import pytest

from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.confirm_buy_in import confirm_buy_in
from pokerman.application.use_cases.request_buy_in import request_buy_in
from pokerman.domain.enums import RoomStatus
from pokerman.domain.errors import RoomHasPendingBuyInsError, UnauthorizedActionError
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestCloseRoom:
    async def test_closes_an_active_room(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None

        closed = await close_room(uow, room_id=room.id, admin_telegram_id=1)

        assert closed.status == RoomStatus.CLOSED
        assert closed.closed_at is not None

    async def test_non_admin_cannot_close(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        with pytest.raises(UnauthorizedActionError):
            await close_room(uow, room_id=room.id, admin_telegram_id=2)

    async def test_blocked_while_pending_buy_ins_exist(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        pending = await request_buy_in(uow, room_id=room.id, player_telegram_id=2)

        with pytest.raises(RoomHasPendingBuyInsError) as exc_info:
            await close_room(uow, room_id=room.id, admin_telegram_id=1)

        assert exc_info.value.pending_buy_in_ids == [pending.buy_in.id]

    async def test_closable_once_pending_buy_ins_are_resolved(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        pending = await request_buy_in(uow, room_id=room.id, player_telegram_id=2)
        assert pending.buy_in.id is not None
        await confirm_buy_in(uow, buy_in_id=pending.buy_in.id, admin_telegram_id=1)

        closed = await close_room(uow, room_id=room.id, admin_telegram_id=1)

        assert closed.status == RoomStatus.CLOSED
