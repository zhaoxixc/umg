from sqlalchemy.orm import Session

from .models import Asset, AssetEvent, DataCenter, Rack, Room, RackGroup


def get_rack_chain(db: Session, rack: Rack) -> tuple[str, str, str]:
    """返回 (datacenter_name, room_name, group_name)。"""
    group = db.get(RackGroup, rack.group_id)
    room = db.get(Room, group.room_id)
    dc = db.get(DataCenter, room.datacenter_id)
    return dc.name, room.name, group.name


def validate_position(db: Session, rack: Rack, u_start: int, u_height: int,
                      exclude_asset_id: int | None = None) -> None:
    if u_start < 1 or u_start + u_height - 1 > rack.u_count:
        raise ValueError(
            f"U 位超出范围：机柜共 {rack.u_count}U，无法放置 {u_start}U-{u_start + u_height - 1}U"
        )
    overlap = rack_assets_u_set(db, rack.id, exclude_asset_id)
    for u in range(u_start, u_start + u_height):
        if u in overlap:
            raise ValueError(f"U 位 {u}U 已被其他资产占用")


def rack_assets_u_set(db: Session, rack_id: int, exclude_asset_id: int | None = None) -> set[int]:
    occupied: set[int] = set()
    q = db.query(Asset).filter(Asset.rack_id == rack_id, Asset.status == "on_rack")
    if exclude_asset_id:
        q = q.filter(Asset.id != exclude_asset_id)
    for a in q.all():
        if a.u_start:
            for u in range(a.u_start, a.u_start + a.u_height):
                occupied.add(u)
    return occupied


def build_message(db: Session, rack: Rack | None, asset: Asset, action: str) -> str:
    if rack:
        dc, room, _ = get_rack_chain(db, rack)
        prefix = f"数据中心:{dc}|机房:{room}|机柜:{rack.name}"
    else:
        prefix = "机柜:-"
    return (
        f"{prefix}|资产编号:{asset.code},资产序列号:{asset.serial}|"
        f"U位:{asset.u_start}U|{action}"
    )


def add_event(db: Session, asset: Asset, event_type: str, message: str) -> None:
    db.add(AssetEvent(asset_id=asset.id, asset_code=asset.code,
                      event_type=event_type, message=message))
