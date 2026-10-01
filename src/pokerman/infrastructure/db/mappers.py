from pokerman.domain.entities import BuyIn, PokerRoom, RoomPlayer, User
from pokerman.domain.value_objects import RoomCode
from pokerman.infrastructure.db.models import BuyInModel, PokerRoomModel, RoomPlayerModel, UserModel


def user_to_domain(model: UserModel) -> User:
    return User(
        telegram_id=model.telegram_id,
        username=model.username,
        display_name=model.display_name,
        created_at=model.created_at,
        default_qr_file_id=model.default_qr_file_id,
        spending_limit=model.spending_limit,
        spending_limit_updated_at=model.spending_limit_updated_at,
    )


def apply_user_to_model(user: User, model: UserModel) -> None:
    model.telegram_id = user.telegram_id
    model.username = user.username
    model.display_name = user.display_name
    model.created_at = user.created_at
    model.default_qr_file_id = user.default_qr_file_id
    model.spending_limit = user.spending_limit
    model.spending_limit_updated_at = user.spending_limit_updated_at


def room_to_domain(model: PokerRoomModel) -> PokerRoom:
    return PokerRoom(
        id=model.id,
        name=model.name,
        code=RoomCode(model.code),
        deep_link_token=model.deep_link_token,
        default_buy_in_amount=model.default_buy_in_amount,
        currency=model.currency,
        admin_telegram_id=model.admin_telegram_id,
        status=model.status,
        qr_file_id=model.qr_file_id,
        created_at=model.created_at,
        closed_at=model.closed_at,
        planned_duration_hours=model.planned_duration_hours,
    )


def apply_room_to_model(room: PokerRoom, model: PokerRoomModel) -> None:
    model.name = room.name
    model.code = str(room.code)
    model.deep_link_token = room.deep_link_token
    model.default_buy_in_amount = room.default_buy_in_amount
    model.currency = room.currency
    model.admin_telegram_id = room.admin_telegram_id
    model.status = room.status
    model.qr_file_id = room.qr_file_id
    model.created_at = room.created_at
    model.closed_at = room.closed_at
    model.planned_duration_hours = room.planned_duration_hours


def room_player_to_domain(model: RoomPlayerModel) -> RoomPlayer:
    return RoomPlayer(
        id=model.id,
        room_id=model.room_id,
        user_telegram_id=model.user_telegram_id,
        joined_at=model.joined_at,
        final_chip_count=model.final_chip_count,
        cashed_out_at=model.cashed_out_at,
    )


def apply_room_player_to_model(member: RoomPlayer, model: RoomPlayerModel) -> None:
    model.room_id = member.room_id
    model.user_telegram_id = member.user_telegram_id
    model.joined_at = member.joined_at
    model.final_chip_count = member.final_chip_count
    model.cashed_out_at = member.cashed_out_at


def buy_in_to_domain(model: BuyInModel) -> BuyIn:
    return BuyIn(
        id=model.id,
        room_player_id=model.room_player_id,
        amount=model.amount,
        status=model.status,
        requested_at=model.requested_at,
        decided_at=model.decided_at,
        decided_by_telegram_id=model.decided_by_telegram_id,
    )


def apply_buy_in_to_model(buy_in: BuyIn, model: BuyInModel) -> None:
    model.room_player_id = buy_in.room_player_id
    model.amount = buy_in.amount
    model.status = buy_in.status
    model.requested_at = buy_in.requested_at
    model.decided_at = buy_in.decided_at
    model.decided_by_telegram_id = buy_in.decided_by_telegram_id
