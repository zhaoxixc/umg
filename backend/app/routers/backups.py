import gzip
import os
import re
import shutil
import subprocess
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from urllib.parse import quote

from .. import models, schemas
from ..config import (BACKUP_DIR, DB_HOST, DB_NAME, DB_PASSWORD,
                      DB_PORT, DB_USER, database_url)
from ..database import get_db
from ..deps import record_audit, require_admin

router = APIRouter(prefix="/api/backups", tags=["backups"])

_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_OK_SUFFIX = (".sql.gz", ".db")


def _ensure_dir() -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    return BACKUP_DIR


def _is_mysql() -> bool:
    return bool(DB_HOST)


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _list_backups() -> list[schemas.BackupInfo]:
    _ensure_dir()
    items = []
    for name in os.listdir(BACKUP_DIR):
        if not name.endswith(_OK_SUFFIX):
            continue
        path = os.path.join(BACKUP_DIR, name)
        items.append(schemas.BackupInfo(
            name=name,
            size=os.path.getsize(path),
            created_at=datetime.fromtimestamp(os.path.getmtime(path)),
        ))
    items.sort(key=lambda x: x.created_at, reverse=True)
    return items


def _safe_name(name: str) -> str:
    if not _NAME_RE.match(name) or not name.endswith(_OK_SUFFIX):
        raise HTTPException(400, "非法的备份文件名")
    path = os.path.join(BACKUP_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(404, "备份文件不存在")
    return path


def _mysql_base() -> list[str]:
    return [
        "mysql", "-h", DB_HOST, "-P", str(DB_PORT), "-u", DB_USER,
        f"--password={DB_PASSWORD}", "--skip-ssl",
    ]


def _kill_other_connections() -> None:
    """恢复前踢掉本库的其他连接，避免 DROP TABLE 被应用连接池的元数据锁阻塞。"""
    base = _mysql_base()
    r = subprocess.run(
        base + ["-B", "-N", "-e",
                "SELECT id FROM information_schema.processlist "
                f"WHERE user='{DB_USER}' AND id <> CONNECTION_ID()"],
        capture_output=True, timeout=30,
    )
    if r.returncode != 0:
        return
    for tok in r.stdout.split():
        pid = tok.strip().decode()
        if pid.isdigit():
            subprocess.run(base + ["-e", f"KILL {pid}"],
                           capture_output=True, timeout=30)


def _dump_mysql(path: str) -> None:
    cmd = [
        "mysqldump", "-h", DB_HOST, "-P", str(DB_PORT), "-u", DB_USER,
        f"--password={DB_PASSWORD}", "--skip-ssl",
        "--single-transaction",
        "--routines", "--triggers", "--events", DB_NAME,
    ]
    try:
        with open(path + ".tmp", "wb") as f:
            proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=600)
        if proc.returncode != 0:
            raise HTTPException(
                500, f"mysqldump 失败: {proc.stderr.decode(errors='ignore')[:300]}")
        with open(path + ".tmp", "rb") as src, gzip.open(path, "wb") as dst:
            shutil.copyfileobj(src, dst)
    finally:
        if os.path.exists(path + ".tmp"):
            os.remove(path + ".tmp")


def _sqlite_file() -> str:
    url = database_url()
    return url.removeprefix("sqlite:///")


def _dump_sqlite(path: str) -> None:
    # 使用 SQLite 在线备份 API，避免复制到写一半的文件
    import sqlite3
    src = sqlite3.connect(_sqlite_file())
    dst = sqlite3.connect(path)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()


def _restore_mysql(path: str) -> None:
    _kill_other_connections()
    sql_path = path[:-3]  # 去掉 .gz
    try:
        with open(sql_path, "wb") as dst:
            # 兜底：MDL 等待最长 30 秒，避免导入进程无限挂起
            dst.write(b"SET SESSION lock_wait_timeout=30;\n")
            with gzip.open(path, "rb") as src:
                shutil.copyfileobj(src, dst)
        cmd = _mysql_base() + [DB_NAME]
        with open(sql_path, "rb") as f:
            proc = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, timeout=600)
    finally:
        if os.path.exists(sql_path):
            os.remove(sql_path)
    if proc.returncode != 0:
        raise HTTPException(
            500, f"恢复失败: {proc.stderr.decode(errors='ignore')[:300]}")


def _restore_sqlite(path: str) -> None:
    from .. import database
    if database.engine:
        database.engine.dispose()
    shutil.copyfile(path, _sqlite_file())


@router.get("", response_model=list[schemas.BackupInfo])
def list_backups(_: models.User = Depends(require_admin)):
    return _list_backups()


@router.post("", response_model=schemas.BackupInfo)
def create_backup(request: Request, db: Session = Depends(get_db),
                  actor: models.User = Depends(require_admin)):
    _ensure_dir()
    name = f"backup_{_stamp()}.sql.gz" if _is_mysql() else f"backup_{_stamp()}.db"
    path = os.path.join(BACKUP_DIR, name)
    try:
        if _is_mysql():
            _dump_mysql(path)
        else:
            _dump_sqlite(path)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"备份失败: {e}")
    record_audit(db, request, actor, "backup_create", f"创建备份:{name}")
    db.commit()
    return schemas.BackupInfo(
        name=name, size=os.path.getsize(path),
        created_at=datetime.fromtimestamp(os.path.getmtime(path)),
    )


@router.get("/{name}/download")
def download_backup(name: str, _: models.User = Depends(require_admin)):
    path = _safe_name(name)
    return FileResponse(
        path, filename=name,
        media_type="application/gzip" if name.endswith(".gz") else "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"},
    )


@router.post("/{name}/restore", response_model=schemas.MessageOut)
def restore_backup(name: str, request: Request, db: Session = Depends(get_db),
                   actor: models.User = Depends(require_admin)):
    path = _safe_name(name)
    # 先写审计：恢复过程会踢掉当前应用的数据库连接
    record_audit(db, request, actor, "backup_restore", f"从备份恢复:{name}")
    db.commit()
    if _is_mysql():
        _restore_mysql(path)
    else:
        _restore_sqlite(path)
    msg = "恢复完成" if _is_mysql() else "恢复完成（SQLite 模式建议重启后端进程）"
    return {"message": msg}


@router.delete("/{name}", response_model=schemas.MessageOut)
def delete_backup(name: str, request: Request, db: Session = Depends(get_db),
                  actor: models.User = Depends(require_admin)):
    path = _safe_name(name)
    os.remove(path)
    record_audit(db, request, actor, "backup_delete", f"删除备份:{name}")
    db.commit()
    return {"message": "已删除"}
