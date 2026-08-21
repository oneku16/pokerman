from pokerman.domain.entities import PokerRoom
from pokerman.domain.errors import UnauthorizedActionError


def ensure_is_admin(room: PokerRoom, telegram_id: int) -> None:
    if room.admin_telegram_id != telegram_id:
        raise UnauthorizedActionError(
            f"user {telegram_id} is not the admin of room {room.id}"
        )
