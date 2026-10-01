import pytest

from pokerman.application.use_cases.close_room import close_room
from pokerman.application.use_cases.confirm_buy_in import confirm_buy_in
from pokerman.application.use_cases.list_ownership_candidates import list_ownership_candidates
from pokerman.application.use_cases.request_buy_in import request_buy_in
from pokerman.application.use_cases.set_default_qr import set_default_qr
from pokerman.application.use_cases.transfer_room_ownership import transfer_room_ownership
from pokerman.application.use_cases.update_default_buy_in import update_default_buy_in
from pokerman.application.use_cases.upload_room_qr import upload_room_qr
from pokerman.domain.enums import BuyInStatus
from pokerman.domain.errors import (
    InvalidOwnershipTransferError,
    NotRoomMemberError,
    RoomClosedError,
    UnauthorizedActionError,
)
from tests.application.fakes import FakeUnitOfWork
from tests.application.helpers import add_player, make_room


class TestTransferRoomOwnership:
    async def test_member_becomes_admin_and_old_admin_becomes_player(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        transfer = await transfer_room_ownership(
            uow, room_id=room.id, admin_telegram_id=1, new_admin_telegram_id=2
        )

        assert transfer.room.admin_telegram_id == 2
        assert transfer.previous_admin_telegram_id == 1
        assert transfer.new_admin.display_name == "Azamat"
        assert await uow.room_players.get(room.id, 1) is not None
        assert uow.committed is True

    async def test_new_admin_can_manage_and_old_admin_cannot(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await transfer_room_ownership(
            uow, room_id=room.id, admin_telegram_id=1, new_admin_telegram_id=2
        )

        with pytest.raises(UnauthorizedActionError):
            await update_default_buy_in(uow, room_id=room.id, admin_telegram_id=1, amount=1000)
        updated = await update_default_buy_in(
            uow, room_id=room.id, admin_telegram_id=2, amount=1000
        )
        assert updated.default_buy_in_amount == 1000

    async def test_new_admin_confirms_buy_ins_and_old_admin_can_buy_in(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await transfer_room_ownership(
            uow, room_id=room.id, admin_telegram_id=1, new_admin_telegram_id=2
        )

        requested = await request_buy_in(uow, room_id=room.id, player_telegram_id=1, amount=500)
        assert requested.buy_in.id is not None
        with pytest.raises(UnauthorizedActionError):
            await confirm_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=1)
        result = await confirm_buy_in(uow, buy_in_id=requested.buy_in.id, admin_telegram_id=2)

        assert result.buy_in.status == BuyInStatus.CONFIRMED
        assert result.player_telegram_id == 1

    async def test_returns_pending_buy_ins_for_the_new_admin(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await add_player(uow, room, telegram_id=3, display_name="Bek")
        await request_buy_in(uow, room_id=room.id, player_telegram_id=3, amount=400)

        transfer = await transfer_room_ownership(
            uow, room_id=room.id, admin_telegram_id=1, new_admin_telegram_id=2
        )

        assert [(p.player_display_name, p.buy_in.amount) for p in transfer.pending_buy_ins] == [
            ("Bek", 400)
        ]

    async def test_uses_the_new_admins_saved_qr(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await upload_room_qr(uow, room_id=room.id, admin_telegram_id=1, qr_file_id="old-qr")
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await set_default_qr(uow, telegram_id=2, qr_file_id="new-qr")

        transfer = await transfer_room_ownership(
            uow, room_id=room.id, admin_telegram_id=1, new_admin_telegram_id=2
        )

        assert transfer.room.qr_file_id == "new-qr"

    async def test_clears_qr_when_new_admin_has_none_saved(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await upload_room_qr(uow, room_id=room.id, admin_telegram_id=1, qr_file_id="old-qr")
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        transfer = await transfer_room_ownership(
            uow, room_id=room.id, admin_telegram_id=1, new_admin_telegram_id=2
        )

        assert transfer.room.qr_file_id is None

    async def test_non_admin_cannot_transfer(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await add_player(uow, room, telegram_id=3, display_name="Bek")

        with pytest.raises(UnauthorizedActionError):
            await transfer_room_ownership(
                uow, room_id=room.id, admin_telegram_id=2, new_admin_telegram_id=3
            )

    async def test_cannot_transfer_to_non_member(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None

        with pytest.raises(NotRoomMemberError):
            await transfer_room_ownership(
                uow, room_id=room.id, admin_telegram_id=1, new_admin_telegram_id=99
            )

    async def test_cannot_transfer_to_self(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None

        with pytest.raises(InvalidOwnershipTransferError):
            await transfer_room_ownership(
                uow, room_id=room.id, admin_telegram_id=1, new_admin_telegram_id=1
            )

    async def test_cannot_transfer_closed_room(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await close_room(uow, room_id=room.id, admin_telegram_id=1)

        with pytest.raises(RoomClosedError):
            await transfer_room_ownership(
                uow, room_id=room.id, admin_telegram_id=1, new_admin_telegram_id=2
            )


class TestListOwnershipCandidates:
    async def test_lists_members_other_than_the_admin_in_join_order(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")
        await add_player(uow, room, telegram_id=3, display_name="Bek")

        candidates = await list_ownership_candidates(uow, room_id=room.id, admin_telegram_id=1)

        assert [u.telegram_id for u in candidates] == [2, 3]

    async def test_empty_when_admin_is_alone(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None

        assert await list_ownership_candidates(uow, room_id=room.id, admin_telegram_id=1) == []

    async def test_non_admin_cannot_list(self) -> None:
        uow = FakeUnitOfWork()
        room = await make_room(uow, admin_telegram_id=1)
        assert room.id is not None
        await add_player(uow, room, telegram_id=2, display_name="Azamat")

        with pytest.raises(UnauthorizedActionError):
            await list_ownership_candidates(uow, room_id=room.id, admin_telegram_id=2)
