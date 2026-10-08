from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user, record_audit
from ..security import (create_token, is_locked, lock_remaining_minutes,
                        record_fail, reset_fails, verify_password)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenOut)
def login(body: schemas.LoginIn, request: Request, db: Session = Depends(get_db)):
    if is_locked(body.username):
        raise HTTPException(
            400, f"失败次数过多，账号已锁定，请 {lock_remaining_minutes(body.username)} 分钟后再试"
        )
    user = db.query(models.User).filter(
        models.User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        record_fail(body.username)
        record_audit(db, request, None, "login_failed", f"用户名:{body.username}")
        db.commit()
        raise HTTPException(400, "用户名或密码错误")
    if not user.is_active:
        raise HTTPException(400, "账号已被禁用，请联系管理员")
    reset_fails(body.username)
    user.last_login_at = datetime.now()
    record_audit(db, request, user, "login", "登录成功")
    db.commit()
    return schemas.TokenOut(
        access_token=create_token(user), id=user.id, username=user.username,
        display_name=user.display_name or user.username, role=user.role,
    )


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.post("/change-password", response_model=schemas.MessageOut)
def change_password(body: schemas.PasswordChangeIn, request: Request,
                    user: models.User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(400, "原密码错误")
    if len(body.new_password) < 6:
        raise HTTPException(400, "新密码长度至少 6 位")
    from ..security import hash_password
    user.password_hash = hash_password(body.new_password)
    record_audit(db, request, user, "change_password", f"用户:{user.username}")
    db.commit()
    return {"message": "密码已修改"}
