from pokerman.application.ports import PlayerStatisticsQuery
from pokerman.application.read_models import PlayerStatistics


async def get_player_statistics(
    stats_query: PlayerStatisticsQuery, *, telegram_id: int
) -> PlayerStatistics:
    return await stats_query.get_statistics(telegram_id)
