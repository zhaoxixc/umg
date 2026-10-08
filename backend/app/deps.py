from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .security import decode_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> models.User:
    if cred is None:
        raise HTTPException(401, "未登录")
    payload = decode_token(cred.credentials)
    if not payload:
        raise HTTPException(401, "登录已过期，请重新登录")
    user = db.get(models.User, payload.get("uid"))
    if not user or not user.is_active:
        raise HTTPException(401, "账号不存在或已被禁用")
    return user


def require_roles(*roles: str):
    def dep(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(403, "没有权限执行此操作")
        return user
    return dep


# 常用角色依赖
require_admin = require_roles("admin")
require_operator = require_roles("admin", "operator")


def record_audit(db: Session, request: Request, user, action: str,
                 detail: str = "") -> None:
    ip = request.client.host if request.client else ""
    db.add(models.AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "",
        action=action, detail=detail, ip=ip,
    ))
