from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pokerman.domain.entities import RoomPlayer
from pokerman.infrastructure.db.mappers import apply_room_player_to_model, room_player_to_domain
from pokerman.infrastructure.db.models import RoomPlayerModel


class SqlAlchemyRoomPlayerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, member: RoomPlayer) -> RoomPlayer:
        model = RoomPlayerModel()
        apply_room_player_to_model(member, model)
        self._session.add(model)
        await self._session.flush()
        member.id = model.id
        return room_player_to_domain(model)

    async def get(self, room_id: int, user_telegram_id: int) -> RoomPlayer | None:
        stmt = select(RoomPlayerModel).where(
            RoomPlayerModel.room_id == room_id,
            RoomPlayerModel.user_telegram_id == user_telegram_id,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return room_player_to_domain(model) if model is not None else None

    async def get_by_id(self, room_player_id: int) -> RoomPlayer | None:
        model = await self._session.get(RoomPlayerModel, room_player_id)
        return room_player_to_domain(model) if model is not None else None

    async def list_for_room(self, room_id: int) -> list[RoomPlayer]:
        stmt = select(RoomPlayerModel).where(RoomPlayerModel.room_id == room_id)
        result = await self._session.execute(stmt)
        return [room_player_to_domain(model) for model in result.scalars().all()]
