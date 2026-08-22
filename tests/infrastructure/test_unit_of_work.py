import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pokerman.application.use_cases.create_room import create_room
from pokerman.application.use_cases.join_room import join_room_by_code
from pokerman.domain.errors import DomainError, DuplicateMembershipError
from pokerman.infrastructure.db.models import PokerRoomModel, UserModel
from pokerman.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from pokerman.infrastructure.room_code_generator import SqlAlchemyRoomCodeGenerator

pytestmark = pytest.mark.integration


class TestSqlAlchemyUnitOfWork:
    async def test_create_room_commits_room_and_admin_membership(
        self, session_factory: async_sessionmaker[AsyncSession], session: AsyncSession
    ) -> None:
        uow = SqlAlchemyUnitOfWork(session_factory)
        codes = SqlAlchemyRoomCodeGenerator(session_factory)

        room = await create_room(
            uow,
            codes,
            admin_telegram_id=1,
            admin_username="elnazar",
            admin_display_name="Elnazar",
            name="Poker Night #24",
            default_buy_in_amount=500,
            currency="KGS",
        )

        stored = (
            await session.execute(select(PokerRoomModel).where(PokerRoomModel.id == room.id))
        ).scalar_one()
        assert stored.name == "Poker Night #24"

        joined = await join_room_by_code(
            SqlAlchemyUnitOfWork(session_factory),
            code=str(room.code),
            telegram_id=2,
            username="azamat",
            display_name="Azamat",
        )
        assert joined.id == room.id

    async def test_failed_use_case_rolls_back_writes_made_earlier_in_the_transaction(
        self, session_factory: async_sessionmaker[AsyncSession], session: AsyncSession
    ) -> None:
        uow = SqlAlchemyUnitOfWork(session_factory)
        codes = SqlAlchemyRoomCodeGenerator(session_factory)
        room = await create_room(
            uow,
            codes,
            admin_telegram_id=1,
            admin_username="original_handle",
            admin_display_name="Elnazar",
            name="Poker Night #24",
            default_buy_in_amount=500,
            currency="KGS",
        )

        # Re-joining as the existing admin refreshes their username before the
        # duplicate-membership check fails; that profile update must not persist.
        with pytest.raises(DuplicateMembershipError):
            await join_room_by_code(
                SqlAlchemyUnitOfWork(session_factory),
                code=str(room.code),
                telegram_id=1,
                username="should_not_persist",
                display_name="Elnazar",
            )

        stored_user = (
            await session.execute(select(UserModel).where(UserModel.telegram_id == 1))
        ).scalar_one()
        assert stored_user.username == "original_handle"
        assert stored_user.display_name == "Elnazar"

    async def test_domain_error_is_a_domain_error_not_a_db_error(
        self, session_factory: async_sessionmaker[AsyncSession]
    ) -> None:
        with pytest.raises(DomainError):
            await join_room_by_code(
                SqlAlchemyUnitOfWork(session_factory),
                code="0000",
                telegram_id=1,
                username=None,
                display_name="Nobody",
            )
