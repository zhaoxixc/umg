from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user

router = APIRouter(prefix="/api/racks", tags=["racks"])


def _get_rack(db: Session, rack_id: int) -> models.Rack:
    rack = db.get(models.Rack, rack_id)
    if not rack:
        raise HTTPException(404, "机柜不存在")
    return rack


@router.get("/{rack_id}/view", response_model=schemas.RackViewOut)
def rack_view(rack_id: int, db: Session = Depends(get_db),
              _: models.User = Depends(get_current_user)):
    rack = _get_rack(db, rack_id)
    dc, room, group = models.DataCenter, models.Room, models.RackGroup
    g = db.get(group, rack.group_id)
    r = db.get(room, g.room_id)
    d = db.get(dc, r.datacenter_id)
    assets = (
        db.query(models.Asset)
        .filter(models.Asset.rack_id == rack_id, models.Asset.status == "on_rack")
        .order_by(models.Asset.u_start.desc())
        .all()
    )
    return schemas.RackViewOut(
        id=rack.id, name=rack.name, u_count=rack.u_count,
        group_name=g.name, room_name=r.name, datacenter_name=d.name,
        assets=[schemas.AssetOut.model_validate(a) for a in assets],
    )


@router.get("/{rack_id}/stats", response_model=schemas.RackStats)
def rack_stats(rack_id: int, db: Session = Depends(get_db),
               _: models.User = Depends(get_current_user)):
    rack = _get_rack(db, rack_id)
    assets = (
        db.query(models.Asset)
        .filter(models.Asset.rack_id == rack_id, models.Asset.status == "on_rack")
        .all()
    )
    used_u = sum(a.u_height for a in assets)
    by_type_rows = (
        db.query(models.Asset.asset_type, func.count(models.Asset.id))
        .filter(models.Asset.rack_id == rack_id, models.Asset.status == "on_rack")
        .group_by(models.Asset.asset_type)
        .all()
    )
    return schemas.RackStats(
        u_count=rack.u_count,
        used_u=used_u,
        free_u=rack.u_count - used_u,
        asset_count=len(assets),
        utilization=round(used_u / rack.u_count * 100, 2) if rack.u_count else 0,
        by_type=[{"name": t or "未分类", "count": c} for t, c in by_type_rows],
    )


@router.get("/{rack_id}/events", response_model=list[schemas.EventOut])
def rack_events(rack_id: int, scope: str = "realtime", limit: int = 50,
                offset: int = 0, db: Session = Depends(get_db),
                _: models.User = Depends(get_current_user)):
    _get_rack(db, rack_id)
    q = (
        db.query(models.AssetEvent)
        .join(models.Asset, models.AssetEvent.asset_id == models.Asset.id)
        .filter(models.Asset.rack_id == rack_id)
        .order_by(models.AssetEvent.created_at.desc(), models.AssetEvent.id.desc())
    )
    if scope == "realtime":
        return q.limit(20).all()
    return q.offset(offset).limit(min(limit, 200)).all()
