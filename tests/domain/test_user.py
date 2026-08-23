from datetime import UTC, datetime, timedelta

import pytest

from pokerman.domain.entities import User
from pokerman.domain.errors import SpendingLimitChangeTooSoonError

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def make_user() -> User:
    return User.register(telegram_id=123, username="azamat", display_name="Azamat", now=NOW)


class TestUser:
    def test_register_creates_user_keyed_by_telegram_id(self) -> None:
        user = User.register(
            telegram_id=123, username="azamat", display_name="Azamat", now=NOW
        )

        assert user.telegram_id == 123
        assert user.username == "azamat"
        assert user.display_name == "Azamat"
        assert user.created_at == NOW

    def test_register_defaults_personal_settings_to_unset(self) -> None:
        user = make_user()

        assert user.default_qr_file_id is None
        assert user.spending_limit is None
        assert user.spending_limit_updated_at is None

    def test_refresh_profile_updates_username_only(self) -> None:
        user = User.register(
            telegram_id=123, username="old_name", display_name="Chosen Name", now=NOW
        )

        user.refresh_profile(username="new_name")

        assert user.telegram_id == 123
        assert user.username == "new_name"
        assert user.display_name == "Chosen Name"
        assert user.created_at == NOW

    def test_refresh_profile_allows_clearing_username(self) -> None:
        user = User.register(telegram_id=123, username="had_one", display_name="X", now=NOW)

        user.refresh_profile(username=None)

        assert user.username is None


class TestUserRename:
    def test_rename_changes_display_name(self) -> None:
        user = make_user()

        user.rename("New Name")

        assert user.display_name == "New Name"

    def test_rename_rejects_blank(self) -> None:
        user = make_user()

        with pytest.raises(ValueError, match="blank"):
            user.rename("   ")


class TestUserDefaultQr:
    def test_set_default_qr_stores_file_id(self) -> None:
        user = make_user()

        user.set_default_qr("tg-file-id")

        assert user.default_qr_file_id == "tg-file-id"

    def test_set_default_qr_can_be_replaced(self) -> None:
        user = make_user()
        user.set_default_qr("first")

        user.set_default_qr("second")

        assert user.default_qr_file_id == "second"


class TestUserSpendingLimit:
    def test_first_set_is_always_allowed(self) -> None:
        user = make_user()

        user.set_spending_limit(500, NOW)

        assert user.spending_limit == 500
        assert user.spending_limit_updated_at == NOW

    def test_rejects_non_positive_limit(self) -> None:
        user = make_user()

        with pytest.raises(ValueError, match="positive"):
            user.set_spending_limit(0, NOW)

    def test_second_change_within_a_week_is_blocked(self) -> None:
        user = make_user()
        user.set_spending_limit(500, NOW)

        with pytest.raises(SpendingLimitChangeTooSoonError) as exc_info:
            user.set_spending_limit(1000, NOW + timedelta(days=3))

        assert exc_info.value.next_allowed_at == NOW + timedelta(days=7)
        assert user.spending_limit == 500

    def test_change_exactly_a_week_later_is_allowed(self) -> None:
        user = make_user()
        user.set_spending_limit(500, NOW)

        user.set_spending_limit(1000, NOW + timedelta(days=7))

        assert user.spending_limit == 1000

    def test_change_after_a_week_is_allowed(self) -> None:
        user = make_user()
        user.set_spending_limit(500, NOW)

        user.set_spending_limit(1000, NOW + timedelta(days=8))

        assert user.spending_limit == 1000
        assert user.spending_limit_updated_at == NOW + timedelta(days=8)

    def test_cooldown_applies_to_lowering_too(self) -> None:
        user = make_user()
        user.set_spending_limit(1000, NOW)

        with pytest.raises(SpendingLimitChangeTooSoonError):
            user.set_spending_limit(200, NOW + timedelta(days=1))
