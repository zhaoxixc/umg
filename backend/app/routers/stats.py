from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/home", response_model=schemas.HomeStats)
def home_stats(db: Session = Depends(get_db),
               _: models.User = Depends(get_current_user)):
    by_type_rows = (
        db.query(models.Asset.asset_type, func.count(models.Asset.id))
        .filter(models.Asset.status == "on_rack")
        .group_by(models.Asset.asset_type)
        .all()
    )
    by_type = [{"name": t or "未分类", "count": c} for t, c in by_type_rows]

    rooms = (
        db.query(models.Room, models.DataCenter)
        .join(models.DataCenter, models.Room.datacenter_id == models.DataCenter.id)
        .order_by(models.DataCenter.id, models.Room.id)
        .all()
    )
    by_room: list[schemas.RoomUtilization] = []
    for room, dc in rooms:
        racks = (
            db.query(models.Rack).join(models.RackGroup)
            .filter(models.RackGroup.room_id == room.id).all()
        )
        if not racks:
            continue
        rack_ids = [r.id for r in racks]
        total_u = sum(r.u_count for r in racks)
        used_u = (
            db.query(func.coalesce(func.sum(models.Asset.u_height), 0))
            .filter(models.Asset.rack_id.in_(rack_ids),
                    models.Asset.status == "on_rack")
            .scalar()
        )
        asset_count = (
            db.query(func.count(models.Asset.id))
            .filter(models.Asset.rack_id.in_(rack_ids),
                    models.Asset.status == "on_rack")
            .scalar()
        )
        by_room.append(schemas.RoomUtilization(
            room=room.name, datacenter=dc.name, racks=len(racks),
            used_u=int(used_u), total_u=total_u,
            utilization=round(used_u / total_u * 100, 2) if total_u else 0,
            asset_count=int(asset_count),
        ))
    by_room.sort(key=lambda x: x.utilization, reverse=True)

    on = db.query(func.count(models.Asset.id)).filter(
        models.Asset.status == "on_rack").scalar()
    off = db.query(func.count(models.Asset.id)).filter(
        models.Asset.status == "off_rack").scalar()
    return schemas.HomeStats(
        by_type=by_type,
        by_room=by_room,
        status_summary={"on_rack": int(on), "off_rack": int(off)},
    )
