import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from . import database as db_module
from . import models  # noqa: F401
from .config import CORS_ORIGINS, LOG_DIR
from .database import Base, init_engine
from .routers import assets, audit, auth, backups, locations, racks, stats, users
from .seed import seed_if_empty, seed_users


def setup_logging() -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger("srvmgpro")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s")
        fh = RotatingFileHandler(os.path.join(LOG_DIR, "app.log"),
                                 maxBytes=5 * 1024 * 1024, backupCount=5,
                                 encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    return logger


logger = setup_logging()


def run_migrations() -> None:
    """启动时执行数据库迁移；已有旧库（无 alembic_version）自动打标。"""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    cfg = Config(str(ini))
    script_location = str(ini.parent / "alembic")
    cfg.set_main_option("script_location", script_location)

    insp = inspect(db_module.engine)
    tables = insp.get_table_names()
    has_version = "alembic_version" in tables
    if tables and not has_version:
        logger.info("existing schema without alembic_version, stamping head")
        command.stamp(cfg, "head")
    else:
        command.upgrade(cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    run_migrations()
    db = db_module.SessionLocal()
    try:
        seed_if_empty(db)
        seed_users(db)
    finally:
        db.close()
    yield


app = FastAPI(title="U位资产管理系统", lifespan=lifespan)

origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def access_log(request: Request, call_next):
    import time
    t0 = time.time()
    resp = await call_next(request)
    ms = (time.time() - t0) * 1000
    ip = request.client.host if request.client else "-"
    logger.info('%s "%s %s" %s %.1fms', ip, request.method,
                request.url.path, resp.status_code, ms)
    return resp


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(audit.router)
app.include_router(backups.router)
app.include_router(locations.router)
app.include_router(racks.router)
app.include_router(stats.router)
app.include_router(assets.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
