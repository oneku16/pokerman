from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pokerman.infrastructure.db.room_ledger_query import SqlAlchemyRoomLedgerQuery
from pokerman.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from pokerman.infrastructure.room_code_generator import SqlAlchemyRoomCodeGenerator


@dataclass(frozen=True, slots=True)
class Deps:
    session_factory: async_sessionmaker[AsyncSession]
    bot_username: str
    default_currency: str

    def uow(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory)

    def code_generator(self) -> SqlAlchemyRoomCodeGenerator:
        return SqlAlchemyRoomCodeGenerator(self.session_factory)

    def ledger_query(self) -> SqlAlchemyRoomLedgerQuery:
        return SqlAlchemyRoomLedgerQuery(self.session_factory)
