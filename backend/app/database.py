import time

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import database_url


class Base(DeclarativeBase):
    pass


engine = None
SessionLocal = None


def init_engine(retries: int = 30, delay: int = 2) -> None:
    global engine, SessionLocal
    url = database_url()
    last_err = None
    for _ in range(retries):
        try:
            engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
            with engine.connect():
                pass
            last_err = None
            break
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(delay)
    if last_err is not None:
        raise RuntimeError(f"cannot connect to database: {last_err}")
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
