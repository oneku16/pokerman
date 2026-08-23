import pytest

from pokerman.application.use_cases.register_user import register_user
from pokerman.application.use_cases.set_default_qr import set_default_qr
from pokerman.application.use_cases.set_spending_limit import set_spending_limit
from pokerman.application.use_cases.update_display_name import update_display_name
from pokerman.domain.errors import SpendingLimitChangeTooSoonError, UserNotFoundError
from tests.application.fakes import FakeUnitOfWork


async def _register(uow: FakeUnitOfWork, telegram_id: int = 1) -> None:
    await register_user(uow, telegram_id=telegram_id, username=None, display_name="Azamat")


class TestUpdateDisplayName:
    async def test_renames_registered_user(self) -> None:
        uow = FakeUnitOfWork()
        await _register(uow)

        user = await update_display_name(uow, telegram_id=1, new_name="Elnazar")

        assert user.display_name == "Elnazar"
        assert uow.committed is True

    async def test_rejects_blank_name(self) -> None:
        uow = FakeUnitOfWork()
        await _register(uow)

        with pytest.raises(ValueError, match="blank"):
            await update_display_name(uow, telegram_id=1, new_name="   ")

    async def test_unknown_user_raises(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(UserNotFoundError):
            await update_display_name(uow, telegram_id=404, new_name="Nobody")


class TestSetDefaultQr:
    async def test_stores_qr_file_id(self) -> None:
        uow = FakeUnitOfWork()
        await _register(uow)

        user = await set_default_qr(uow, telegram_id=1, qr_file_id="tg-file-id")

        assert user.default_qr_file_id == "tg-file-id"

    async def test_unknown_user_raises(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(UserNotFoundError):
            await set_default_qr(uow, telegram_id=404, qr_file_id="tg-file-id")


class TestSetSpendingLimit:
    async def test_first_set_succeeds(self) -> None:
        uow = FakeUnitOfWork()
        await _register(uow)

        user = await set_spending_limit(uow, telegram_id=1, limit=500)

        assert user.spending_limit == 500
        assert user.spending_limit_updated_at is not None

    async def test_immediate_second_change_is_blocked_by_cooldown(self) -> None:
        uow = FakeUnitOfWork()
        await _register(uow)
        await set_spending_limit(uow, telegram_id=1, limit=500)

        with pytest.raises(SpendingLimitChangeTooSoonError):
            await set_spending_limit(uow, telegram_id=1, limit=1000)

    async def test_rejects_non_positive_limit(self) -> None:
        uow = FakeUnitOfWork()
        await _register(uow)

        with pytest.raises(ValueError, match="positive"):
            await set_spending_limit(uow, telegram_id=1, limit=0)

    async def test_unknown_user_raises(self) -> None:
        uow = FakeUnitOfWork()

        with pytest.raises(UserNotFoundError):
            await set_spending_limit(uow, telegram_id=404, limit=500)
