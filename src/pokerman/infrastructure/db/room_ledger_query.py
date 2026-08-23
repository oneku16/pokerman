from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pokerman.application.read_models import PlayerLedgerRow
from pokerman.domain.enums import BuyInStatus
from pokerman.infrastructure.db.models import BuyInModel, RoomPlayerModel, UserModel


class SqlAlchemyRoomLedgerQuery:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def player_totals(self, room_id: int) -> list[PlayerLedgerRow]:
        confirmed_total = func.coalesce(
            func.sum(BuyInModel.amount).filter(BuyInModel.status == BuyInStatus.CONFIRMED), 0
        )
        confirmed_count = func.count(BuyInModel.id).filter(
            BuyInModel.status == BuyInStatus.CONFIRMED
        )
        stmt = (
            select(
                RoomPlayerModel.id,
                RoomPlayerModel.user_telegram_id,
                UserModel.display_name,
                confirmed_total,
                confirmed_count,
                RoomPlayerModel.final_chip_count,
            )
            .join(UserModel, UserModel.telegram_id == RoomPlayerModel.user_telegram_id)
            .outerjoin(BuyInModel, BuyInModel.room_player_id == RoomPlayerModel.id)
            .where(RoomPlayerModel.room_id == room_id)
            .group_by(
                RoomPlayerModel.id,
                RoomPlayerModel.user_telegram_id,
                UserModel.display_name,
                RoomPlayerModel.final_chip_count,
            )
        )
        async with self._session_factory() as session:
            result = await session.execute(stmt)
            return [
                PlayerLedgerRow(
                    room_player_id=row[0],
                    user_telegram_id=row[1],
                    display_name=row[2],
                    confirmed_total=int(row[3]),
                    confirmed_count=int(row[4]),
                    final_chip_count=row[5],
                )
                for row in result.all()
            ]
