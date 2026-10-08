from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, record_audit, require_admin

router = APIRouter(prefix="/api/locations", tags=["locations"])


def _onrack_count(db: Session, rack_ids: list[int]) -> int:
    if not rack_ids:
        return 0
    return (
        db.query(func.count(models.Asset.id))
        .filter(
            models.Asset.rack_id.in_(rack_ids),
            models.Asset.status == "on_rack",
        )
        .scalar()
    )


# ---------- 树 ----------
@router.get("/tree", response_model=list[schemas.TreeNode])
def tree(q: str = "", db: Session = Depends(get_db),
        _: models.User = Depends(get_current_user)):
    dcs = db.query(models.DataCenter).order_by(models.DataCenter.id).all()
    keyword = q.strip().lower()

    def rack_hit(rack: models.Rack) -> bool:
        if not keyword:
            return True
        if keyword in rack.name.lower():
            return True
        return any(
            keyword in (a.code + a.serial + a.name).lower()
            for a in db.query(models.Asset)
            .filter(models.Asset.rack_id == rack.id, models.Asset.status == "on_rack")
            .all()
        )

    nodes = []
    for dc in dcs:
        dc_children = []
        for room in dc.rooms:
            room_children = []
            for g in room.groups:
                racks = [r for r in g.racks if rack_hit(r)]
                if keyword and not racks:
                    continue
                room_children.append(schemas.TreeNode(
                    id=g.id, name=g.name, type="group",
                    children=[schemas.TreeNode(
                        id=r.id, name=r.name, type="rack", u_count=r.u_count
                    ) for r in racks],
                ))
            if keyword and not room_children:
                continue
            dc_children.append(schemas.TreeNode(
                id=room.id, name=room.name, type="room", children=room_children))
        if keyword and not dc_children:
            continue
        nodes.append(schemas.TreeNode(
            id=dc.id, name=dc.name, type="datacenter", children=dc_children))
    return nodes


# ---------- 数据中心 ----------
@router.post("/datacenters", response_model=schemas.DataCenterOut)
def create_dc(body: schemas.DataCenterIn, request: Request,
              db: Session = Depends(get_db),
              actor: models.User = Depends(require_admin)):
    if db.query(models.DataCenter).filter_by(name=body.name).first():
        raise HTTPException(400, "数据中心已存在")
    dc = models.DataCenter(name=body.name)
    db.add(dc)
    db.flush()
    record_audit(db, request, actor, "dc_create", f"新增数据中心:{body.name}")
    db.commit()
    db.refresh(dc)
    return dc


@router.put("/datacenters/{dc_id}", response_model=schemas.DataCenterOut)
def update_dc(dc_id: int, body: schemas.NameIn, request: Request,
              db: Session = Depends(get_db),
              actor: models.User = Depends(require_admin)):
    dc = db.get(models.DataCenter, dc_id)
    if not dc:
        raise HTTPException(404, "数据中心不存在")
    dup = db.query(models.DataCenter).filter(
        models.DataCenter.name == body.name, models.DataCenter.id != dc_id).first()
    if dup:
        raise HTTPException(400, "数据中心已存在")
    dc.name = body.name
    record_audit(db, request, actor, "dc_update", f"数据中心改名:{body.name}")
    db.commit()
    db.refresh(dc)
    return dc


@router.delete("/datacenters/{dc_id}", response_model=schemas.MessageOut)
def delete_dc(dc_id: int, request: Request, db: Session = Depends(get_db),
              actor: models.User = Depends(require_admin)):
    dc = db.get(models.DataCenter, dc_id)
    if not dc:
        raise HTTPException(404, "数据中心不存在")
    rack_ids = [r.id for room in dc.rooms for g in room.groups for r in g.racks]
    used = _onrack_count(db, rack_ids)
    if used:
        raise HTTPException(400, f"该数据中心下仍有 {used} 台在架资产，请先下架")
    name = dc.name
    db.delete(dc)
    record_audit(db, request, actor, "dc_delete", f"删除数据中心:{name}")
    db.commit()
    return {"message": "已删除"}


# ---------- 机房 ----------
@router.post("/rooms", response_model=schemas.RoomOut)
def create_room(body: schemas.RoomIn, request: Request,
                db: Session = Depends(get_db),
                actor: models.User = Depends(require_admin)):
    if not db.get(models.DataCenter, body.datacenter_id):
        raise HTTPException(404, "数据中心不存在")
    room = models.Room(**body.model_dump())
    db.add(room)
    db.flush()
    record_audit(db, request, actor, "room_create", f"新增机房:{body.name}")
    db.commit()
    db.refresh(room)
    return room


@router.put("/rooms/{room_id}", response_model=schemas.RoomOut)
def update_room(room_id: int, body: schemas.NameIn, request: Request,
                db: Session = Depends(get_db),
                actor: models.User = Depends(require_admin)):
    room = db.get(models.Room, room_id)
    if not room:
        raise HTTPException(404, "机房不存在")
    room.name = body.name
    record_audit(db, request, actor, "room_update", f"机房改名:{body.name}")
    db.commit()
    db.refresh(room)
    return room


@router.delete("/rooms/{room_id}", response_model=schemas.MessageOut)
def delete_room(room_id: int, request: Request, db: Session = Depends(get_db),
                actor: models.User = Depends(require_admin)):
    room = db.get(models.Room, room_id)
    if not room:
        raise HTTPException(404, "机房不存在")
    rack_ids = [r.id for g in room.groups for r in g.racks]
    used = _onrack_count(db, rack_ids)
    if used:
        raise HTTPException(400, f"该机房下仍有 {used} 台在架资产，请先下架")
    name = room.name
    db.delete(room)
    record_audit(db, request, actor, "room_delete", f"删除机房:{name}")
    db.commit()
    return {"message": "已删除"}


# ---------- 机柜列 ----------
@router.post("/groups", response_model=schemas.RackGroupOut)
def create_group(body: schemas.RackGroupIn, request: Request,
                 db: Session = Depends(get_db),
                 actor: models.User = Depends(require_admin)):
    if not db.get(models.Room, body.room_id):
        raise HTTPException(404, "机房不存在")
    g = models.RackGroup(**body.model_dump())
    db.add(g)
    db.flush()
    record_audit(db, request, actor, "group_create", f"新增机柜列:{body.name}")
    db.commit()
    db.refresh(g)
    return g


@router.put("/groups/{group_id}", response_model=schemas.RackGroupOut)
def update_group(group_id: int, body: schemas.NameIn, request: Request,
                 db: Session = Depends(get_db),
                 actor: models.User = Depends(require_admin)):
    g = db.get(models.RackGroup, group_id)
    if not g:
        raise HTTPException(404, "机柜列不存在")
    g.name = body.name
    record_audit(db, request, actor, "group_update", f"机柜列改名:{body.name}")
    db.commit()
    db.refresh(g)
    return g


@router.delete("/groups/{group_id}", response_model=schemas.MessageOut)
def delete_group(group_id: int, request: Request, db: Session = Depends(get_db),
                 actor: models.User = Depends(require_admin)):
    g = db.get(models.RackGroup, group_id)
    if not g:
        raise HTTPException(404, "机柜列不存在")
    used = _onrack_count(db, [r.id for r in g.racks])
    if used:
        raise HTTPException(400, f"该机柜列下仍有 {used} 台在架资产，请先下架")
    name = g.name
    db.delete(g)
    record_audit(db, request, actor, "group_delete", f"删除机柜列:{name}")
    db.commit()
    return {"message": "已删除"}


# ---------- 机柜 ----------
@router.post("/racks", response_model=schemas.RackOut)
def create_rack(body: schemas.RackIn, request: Request,
                db: Session = Depends(get_db),
                actor: models.User = Depends(require_admin)):
    if not db.get(models.RackGroup, body.group_id):
        raise HTTPException(404, "机柜列不存在")
    rack = models.Rack(**body.model_dump())
    db.add(rack)
    db.flush()
    record_audit(db, request, actor, "rack_create",
                 f"新增机柜:{body.name}({body.u_count}U)")
    db.commit()
    db.refresh(rack)
    return rack


@router.put("/racks/{rack_id}", response_model=schemas.RackOut)
def update_rack(rack_id: int, body: schemas.RackUpdate, request: Request,
                db: Session = Depends(get_db),
                actor: models.User = Depends(require_admin)):
    rack = db.get(models.Rack, rack_id)
    if not rack:
        raise HTTPException(404, "机柜不存在")
    data = body.model_dump(exclude_unset=True)
    if "u_count" in data:
        max_u = (
            db.query(func.max(models.Asset.u_start + models.Asset.u_height - 1))
            .filter(models.Asset.rack_id == rack_id, models.Asset.status == "on_rack")
            .scalar()
        )
        if max_u and data["u_count"] < max_u:
            raise HTTPException(400, f"机柜内资产最高占用到 {max_u}U，U 数不能小于该值")
        rack.u_count = data["u_count"]
    if "name" in data:
        rack.name = data["name"]
    record_audit(db, request, actor, "rack_update", f"更新机柜:{rack.name}")
    db.commit()
    db.refresh(rack)
    return rack


@router.delete("/racks/{rack_id}", response_model=schemas.MessageOut)
def delete_rack(rack_id: int, request: Request, db: Session = Depends(get_db),
                actor: models.User = Depends(require_admin)):
    rack = db.get(models.Rack, rack_id)
    if not rack:
        raise HTTPException(404, "机柜不存在")
    used = db.query(models.Asset).filter(
        models.Asset.rack_id == rack_id, models.Asset.status == "on_rack").count()
    if used:
        raise HTTPException(400, f"机柜内仍有 {used} 台在架资产，请先下架")
    name = rack.name
    db.delete(rack)
    record_audit(db, request, actor, "rack_delete", f"删除机柜:{name}")
    db.commit()
    return {"message": "已删除"}
