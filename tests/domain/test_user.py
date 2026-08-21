from datetime import UTC, datetime

from pokerman.domain.entities import User

NOW = datetime(2026, 1, 1, tzinfo=UTC)


class TestUser:
    def test_register_creates_user_keyed_by_telegram_id(self) -> None:
        user = User.register(
            telegram_id=123, username="azamat", display_name="Azamat", now=NOW
        )

        assert user.telegram_id == 123
        assert user.username == "azamat"
        assert user.display_name == "Azamat"
        assert user.created_at == NOW

    def test_refresh_profile_updates_mutable_fields_only(self) -> None:
        user = User.register(
            telegram_id=123, username="old_name", display_name="Old", now=NOW
        )

        user.refresh_profile(username="new_name", display_name="New")

        assert user.telegram_id == 123
        assert user.username == "new_name"
        assert user.display_name == "New"
        assert user.created_at == NOW

    def test_refresh_profile_allows_clearing_username(self) -> None:
        user = User.register(telegram_id=123, username="had_one", display_name="X", now=NOW)

        user.refresh_profile(username=None, display_name="X")

        assert user.username is None
