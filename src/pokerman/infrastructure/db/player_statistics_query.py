from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pokerman.application.read_models import PlayerStatistics
from pokerman.domain.enums import BuyInStatus, RoomStatus
from pokerman.infrastructure.db.models import BuyInModel, PokerRoomModel, RoomPlayerModel, UserModel


class SqlAlchemyPlayerStatisticsQuery:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_statistics(self, telegram_id: int) -> PlayerStatistics:
        async with self._session_factory() as session:
            display_name = await session.scalar(
                select(UserModel.display_name).where(UserModel.telegram_id == telegram_id)
            )
            games_played = await session.scalar(
                select(func.count(func.distinct(RoomPlayerModel.room_id)))
                .join(PokerRoomModel, PokerRoomModel.id == RoomPlayerModel.room_id)
                .where(
                    RoomPlayerModel.user_telegram_id == telegram_id,
                    PokerRoomModel.status == RoomStatus.CLOSED,
                )
            )
            spend_row = (
                await session.execute(
                    select(
                        func.coalesce(func.sum(BuyInModel.amount), 0),
                        func.count(BuyInModel.id),
                    )
                    .join(RoomPlayerModel, RoomPlayerModel.id == BuyInModel.room_player_id)
                    .where(
                        RoomPlayerModel.user_telegram_id == telegram_id,
                        BuyInModel.status == BuyInStatus.CONFIRMED,
                    )
                )
            ).one()

            confirmed_per_room_player = (
                select(
                    BuyInModel.room_player_id,
                    func.sum(BuyInModel.amount).label("confirmed_total"),
                )
                .where(BuyInModel.status == BuyInStatus.CONFIRMED)
                .group_by(BuyInModel.room_player_id)
                .subquery()
            )
            cash_out_rows = (
                await session.execute(
                    select(
                        RoomPlayerModel.final_chip_count,
                        func.coalesce(confirmed_per_room_player.c.confirmed_total, 0),
                    )
                    .outerjoin(
                        confirmed_per_room_player,
                        confirmed_per_room_player.c.room_player_id == RoomPlayerModel.id,
                    )
                    .where(
                        RoomPlayerModel.user_telegram_id == telegram_id,
                        RoomPlayerModel.final_chip_count.is_not(None),
                    )
                )
            ).all()

            total_cashed_out = sum(row[0] for row in cash_out_rows)
            net_result = sum(row[0] - row[1] for row in cash_out_rows)

            return PlayerStatistics(
                telegram_id=telegram_id,
                display_name=display_name or str(telegram_id),
                games_played=games_played or 0,
                total_buy_in_count=spend_row[1],
                total_spent=spend_row[0],
                total_cashed_out=total_cashed_out,
                net_result=net_result,
            )
