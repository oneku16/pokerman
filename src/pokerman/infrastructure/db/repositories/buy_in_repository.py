from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pokerman.domain.entities import BuyIn
from pokerman.domain.enums import BuyInStatus
from pokerman.infrastructure.db.mappers import apply_buy_in_to_model, buy_in_to_domain
from pokerman.infrastructure.db.models import BuyInModel, RoomPlayerModel


class SqlAlchemyBuyInRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, buy_in: BuyIn) -> BuyIn:
        model = BuyInModel()
        apply_buy_in_to_model(buy_in, model)
        self._session.add(model)
        await self._session.flush()
        buy_in.id = model.id
        return buy_in_to_domain(model)

    async def get_by_id(self, buy_in_id: int) -> BuyIn | None:
        model = await self._session.get(BuyInModel, buy_in_id)
        return buy_in_to_domain(model) if model is not None else None

    async def save(self, buy_in: BuyIn) -> None:
        assert buy_in.id is not None
        model = await self._session.get(BuyInModel, buy_in.id)
        assert model is not None
        apply_buy_in_to_model(buy_in, model)

    async def list_pending_for_room(self, room_id: int) -> list[BuyIn]:
        stmt = (
            select(BuyInModel)
            .join(RoomPlayerModel, RoomPlayerModel.id == BuyInModel.room_player_id)
            .where(RoomPlayerModel.room_id == room_id, BuyInModel.status == BuyInStatus.PENDING)
        )
        result = await self._session.execute(stmt)
        return [buy_in_to_domain(model) for model in result.scalars().all()]

    async def list_for_room_player(self, room_player_id: int) -> list[BuyIn]:
        stmt = select(BuyInModel).where(BuyInModel.room_player_id == room_player_id)
        result = await self._session.execute(stmt)
        return [buy_in_to_domain(model) for model in result.scalars().all()]
