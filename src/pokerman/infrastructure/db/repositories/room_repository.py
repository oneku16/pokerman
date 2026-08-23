from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pokerman.domain.entities import PokerRoom
from pokerman.domain.enums import RoomStatus
from pokerman.domain.value_objects import RoomCode
from pokerman.infrastructure.db.mappers import apply_room_to_model, room_to_domain
from pokerman.infrastructure.db.models import PokerRoomModel, RoomPlayerModel


class SqlAlchemyRoomRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, room: PokerRoom) -> PokerRoom:
        model = PokerRoomModel()
        apply_room_to_model(room, model)
        self._session.add(model)
        await self._session.flush()
        room.id = model.id
        return room_to_domain(model)

    async def get_by_id(self, room_id: int) -> PokerRoom | None:
        model = await self._session.get(PokerRoomModel, room_id)
        return room_to_domain(model) if model is not None else None

    async def get_by_code(self, code: RoomCode) -> PokerRoom | None:
        stmt = select(PokerRoomModel).where(
            PokerRoomModel.code == str(code), PokerRoomModel.status == RoomStatus.ACTIVE
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return room_to_domain(model) if model is not None else None

    async def get_by_deep_link_token(self, token: str) -> PokerRoom | None:
        stmt = select(PokerRoomModel).where(PokerRoomModel.deep_link_token == token)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return room_to_domain(model) if model is not None else None

    async def is_code_taken_by_active_room(self, code: RoomCode) -> bool:
        stmt = select(PokerRoomModel.id).where(
            PokerRoomModel.code == str(code), PokerRoomModel.status == RoomStatus.ACTIVE
        )
        result = (await self._session.execute(stmt)).first()
        return result is not None

    async def save(self, room: PokerRoom) -> None:
        assert room.id is not None
        model = await self._session.get(PokerRoomModel, room.id)
        assert model is not None
        apply_room_to_model(room, model)

    async def list_for_user(
        self, telegram_id: int, *, limit: int | None = None
    ) -> list[PokerRoom]:
        stmt = (
            select(PokerRoomModel)
            .join(RoomPlayerModel, RoomPlayerModel.room_id == PokerRoomModel.id)
            .where(RoomPlayerModel.user_telegram_id == telegram_id)
            .order_by(RoomPlayerModel.joined_at.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return [room_to_domain(model) for model in result.scalars().all()]
