from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class DataCenter(Base):
    __tablename__ = "datacenters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)

    rooms: Mapped[list["Room"]] = relationship(
        back_populates="datacenter", cascade="all, delete-orphan"
    )


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datacenter_id: Mapped[int] = mapped_column(ForeignKey("datacenters.id"))
    name: Mapped[str] = mapped_column(String(128))

    datacenter: Mapped["DataCenter"] = relationship(back_populates="rooms")
    groups: Mapped[list["RackGroup"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )


class RackGroup(Base):
    """机柜列 / 微模块"""

    __tablename__ = "rack_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    name: Mapped[str] = mapped_column(String(128))

    room: Mapped["Room"] = relationship(back_populates="groups")
    racks: Mapped[list["Rack"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class Rack(Base):
    __tablename__ = "racks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("rack_groups.id"))
    name: Mapped[str] = mapped_column(String(128))
    u_count: Mapped[int] = mapped_column(Integer, default=42)

    group: Mapped["RackGroup"] = relationship(back_populates="racks")
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="rack", foreign_keys="Asset.rack_id"
    )


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("rack_id", "u_start", name="uq_rack_ustart"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)  # 资产编号
    serial: Mapped[str] = mapped_column(String(64), default="")  # 资产序列号
    name: Mapped[str] = mapped_column(String(128))  # 资产名称
    tag_id: Mapped[str] = mapped_column(String(32), default="")  # 标签ID
    status: Mapped[str] = mapped_column(String(16), default="off_rack")  # on_rack / off_rack
    asset_type: Mapped[str] = mapped_column(String(32), default="服务器")
    brand: Mapped[str] = mapped_column(String(64), default="")
    model: Mapped[str] = mapped_column(String(64), default="")
    ip_address: Mapped[str] = mapped_column(String(64), default="")  # 业务IP地址
    bmc_address: Mapped[str] = mapped_column(String(64), default="")  # BMC远程管理地址
    remark: Mapped[str] = mapped_column(String(255), default="")  # 备注
    rack_id: Mapped[int | None] = mapped_column(ForeignKey("racks.id"), nullable=True)
    u_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    u_height: Mapped[int] = mapped_column(Integer, default=1)

    rack: Mapped["Rack | None"] = relationship(back_populates="assets", foreign_keys=[rack_id])


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    display_name: Mapped[str] = mapped_column(String(64), default="")
    role: Mapped[str] = mapped_column(String(16), default="viewer")  # admin / operator / viewer
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str] = mapped_column(String(64), default="")
    action: Mapped[str] = mapped_column(String(32))
    detail: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class AssetEvent(Base):
    __tablename__ = "asset_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    asset_code: Mapped[str] = mapped_column(String(64), default="")
    event_type: Mapped[str] = mapped_column(String(16))  # rack_on / rack_off / move
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
