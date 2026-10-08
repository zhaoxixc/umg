from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import require_admin

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[schemas.AuditOut])
def list_audit(username: str = "", action: str = "", limit: int = 50,
               offset: int = 0, db: Session = Depends(get_db),
               _: models.User = Depends(require_admin)):
    q = db.query(models.AuditLog)
    if username.strip():
        q = q.filter(models.AuditLog.username.contains(username.strip()))
    if action.strip():
        q = q.filter(models.AuditLog.action == action.strip())
    return (q.order_by(models.AuditLog.id.desc())
             .offset(offset).limit(min(limit, 200)).all())
