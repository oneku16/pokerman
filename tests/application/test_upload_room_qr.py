import pytest

from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.upload_room_qr import upload_room_qr
from pokerman.domain.errors import RoomClosedError, UnauthorizedActionError
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestUploadRoomQr:
    async def test_admin_can_set_qr(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None

        updated = await upload_room_qr(
            uow, room_id=room.id, admin_telegram_id=1, qr_file_id="tg-file-id"
        )

        assert updated.qr_file_id == "tg-file-id"

    async def test_non_admin_cannot_set_qr(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        with pytest.raises(UnauthorizedActionError):
            await upload_room_qr(uow, room_id=room.id, admin_telegram_id=2, qr_file_id="tg-file-id")

    async def test_cannot_set_qr_on_closed_room(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await close_room(uow, room_id=room.id, admin_telegram_id=1)

        with pytest.raises(RoomClosedError):
            await upload_room_qr(uow, room_id=room.id, admin_telegram_id=1, qr_file_id="tg-file-id")
