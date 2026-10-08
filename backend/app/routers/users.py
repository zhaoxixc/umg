from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import record_audit, require_admin
from ..security import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])


def _guard_target(db: Session, target: models.User, actor: models.User,
                  new_role: str | None = None, new_active: bool | None = None) -> None:
    if target.id == actor.id:
        if new_role and new_role != "admin":
            raise HTTPException(400, "不能降级自己的角色")
        if new_active is False:
            raise HTTPException(400, "不能禁用自己的账号")
    if new_active is False and target.role == "admin":
        last_admin = (
            db.query(models.User)
            .filter(models.User.role == "admin", models.User.is_active.is_(True))
            .count()
        )
        if last_admin <= 1:
            raise HTTPException(400, "系统至少需要保留一个启用的管理员")


@router.get("", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db),
               _: models.User = Depends(require_admin)):
    return db.query(models.User).order_by(models.User.id).all()


@router.post("", response_model=schemas.UserOut)
def create_user(body: schemas.UserIn, request: Request,
                db: Session = Depends(get_db),
                actor: models.User = Depends(require_admin)):
    if len(body.password) < 6:
        raise HTTPException(400, "密码长度至少 6 位")
    if db.query(models.User).filter(
            models.User.username == body.username).first():
        raise HTTPException(400, f"用户名 {body.username} 已存在")
    user = models.User(
        username=body.username, password_hash=hash_password(body.password),
        display_name=body.display_name, role=body.role,
    )
    db.add(user)
    record_audit(db, request, actor, "user_create",
                 f"创建用户:{body.username},角色:{body.role}")
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(user_id: int, body: schemas.UserUpdate, request: Request,
                db: Session = Depends(get_db),
                actor: models.User = Depends(require_admin)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    data = body.model_dump(exclude_unset=True)
    _guard_target(db, user, actor, data.get("role"), data.get("is_active"))
    if "password" in data:
        if not data["password"] or len(data["password"]) < 6:
            raise HTTPException(400, "密码长度至少 6 位")
        user.password_hash = hash_password(data.pop("password"))
        record_audit(db, request, actor, "user_reset_password",
                     f"重置用户:{user.username} 的密码")
    for k, v in data.items():
        setattr(user, k, v)
    if data:
        record_audit(db, request, actor, "user_update",
                     f"更新用户:{user.username},字段:{','.join(data)}")
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=schemas.MessageOut)
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db),
                actor: models.User = Depends(require_admin)):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.id == actor.id:
        raise HTTPException(400, "不能删除自己的账号")
    db.delete(user)
    record_audit(db, request, actor, "user_delete", f"删除用户:{user.username}")
    db.commit()
    return {"message": "已删除"}
