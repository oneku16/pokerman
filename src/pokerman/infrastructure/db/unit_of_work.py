from __future__ import annotations

from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pokerman.infrastructure.db.repositories.buy_in_repository import SqlAlchemyBuyInRepository
from pokerman.infrastructure.db.repositories.room_player_repository import (
    SqlAlchemyRoomPlayerRepository,
)
from pokerman.infrastructure.db.repositories.room_repository import SqlAlchemyRoomRepository
from pokerman.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        session = self._session_factory()
        self._session = session
        self.users = SqlAlchemyUserRepository(session)
        self.rooms = SqlAlchemyRoomRepository(session)
        self.room_players = SqlAlchemyRoomPlayerRepository(session)
        self.buy_ins = SqlAlchemyBuyInRepository(session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._session is not None
        try:
            if exc_type is not None:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        assert self._session is not None
        await self._session.commit()

    async def rollback(self) -> None:
        assert self._session is not None
        await self._session.rollback()
