from datetime import UTC, datetime

import pytest

from pokerman.domain.entities import PokerRoom
from pokerman.domain.enums import RoomStatus
from pokerman.domain.errors import RoomClosedError
from pokerman.domain.value_objects import RoomCode

NOW = datetime(2026, 1, 1, tzinfo=UTC)
LATER = datetime(2026, 1, 1, hour=23, tzinfo=UTC)


def make_room(**overrides: object) -> PokerRoom:
    defaults: dict[str, object] = {
        "name": "Poker Night #24",
        "code": RoomCode("4821"),
        "deep_link_token": "tok_abc123",
        "default_buy_in_amount": 500,
        "currency": "KGS",
        "admin_telegram_id": 1,
        "now": NOW,
    }
    defaults.update(overrides)
    return PokerRoom.open(**defaults)  # type: ignore[arg-type]


class TestPokerRoomOpen:
    def test_open_starts_active_with_no_qr(self) -> None:
        room = make_room()

        assert room.id is None
        assert room.status == RoomStatus.ACTIVE
        assert room.qr_file_id is None
        assert room.closed_at is None
        assert room.created_at == NOW

    def test_rejects_blank_name(self) -> None:
        with pytest.raises(ValueError, match="blank"):
            make_room(name="   ")

    def test_rejects_non_positive_default_buy_in(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            make_room(default_buy_in_amount=0)


class TestPokerRoomQr:
    def test_set_qr_stores_file_id(self) -> None:
        room = make_room()

        room.set_qr("telegram-file-id-123")

        assert room.qr_file_id == "telegram-file-id-123"

    def test_set_qr_fails_on_closed_room(self) -> None:
        room = make_room()
        room.close(LATER)

        with pytest.raises(RoomClosedError):
            room.set_qr("telegram-file-id-123")


class TestPokerRoomDefaultBuyIn:
    def test_update_default_buy_in_changes_amount(self) -> None:
        room = make_room()

        room.update_default_buy_in(1000)

        assert room.default_buy_in_amount == 1000

    def test_update_default_buy_in_rejects_non_positive(self) -> None:
        room = make_room()

        with pytest.raises(ValueError, match="positive"):
            room.update_default_buy_in(0)

    def test_update_default_buy_in_fails_on_closed_room(self) -> None:
        room = make_room()
        room.close(LATER)

        with pytest.raises(RoomClosedError):
            room.update_default_buy_in(1000)


class TestPokerRoomClose:
    def test_close_transitions_to_closed(self) -> None:
        room = make_room()

        room.close(LATER)

        assert room.status == RoomStatus.CLOSED
        assert room.closed_at == LATER

    def test_close_is_not_idempotent(self) -> None:
        room = make_room()
        room.close(LATER)

        with pytest.raises(RoomClosedError):
            room.close(LATER)


class TestPokerRoomEnsureActive:
    def test_ensure_active_passes_on_active_room(self) -> None:
        make_room().ensure_active()

    def test_ensure_active_raises_on_closed_room(self) -> None:
        room = make_room()
        room.close(LATER)

        with pytest.raises(RoomClosedError):
            room.ensure_active()
