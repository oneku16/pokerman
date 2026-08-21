from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pokerman.domain.errors import RoomCodeExhaustedError
from pokerman.domain.value_objects import RoomCode
from pokerman.infrastructure.db.repositories.room_repository import SqlAlchemyRoomRepository

_MAX_ATTEMPTS = 25


class SqlAlchemyRoomCodeGenerator:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def generate_unique_code(self) -> RoomCode:
        async with self._session_factory() as session:
            rooms = SqlAlchemyRoomRepository(session)
            for _ in range(_MAX_ATTEMPTS):
                code = RoomCode.generate()
                if not await rooms.is_code_taken_by_active_room(code):
                    return code
        raise RoomCodeExhaustedError("could not find a free room code")
