from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class DataCenterIn(BaseModel):
    name: str


class DataCenterOut(DataCenterIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RoomIn(BaseModel):
    name: str
    datacenter_id: int


class RoomOut(RoomIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RackGroupIn(BaseModel):
    name: str
    room_id: int


class RackGroupOut(RackGroupIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class RackIn(BaseModel):
    name: str
    group_id: int
    u_count: int = 42

    @field_validator("u_count")
    @classmethod
    def check_u(cls, v: int) -> int:
        if not 1 <= v <= 60:
            raise ValueError("u_count 必须在 1-60 之间")
        return v


class RackOut(RackIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class AssetIn(BaseModel):
    code: str
    serial: str = ""
    name: str
    tag_id: str = ""
    asset_type: str = "服务器"
    brand: str = ""
    model: str = ""
    ip_address: str = ""
    bmc_address: str = ""
    remark: str = ""
    rack_id: int | None = None
    u_start: int | None = None
    u_height: int = 1

    @field_validator("u_height")
    @classmethod
    def check_h(cls, v: int) -> int:
        if not 1 <= v <= 10:
            raise ValueError("u_height 必须在 1-10U 之间")
        return v


class AssetUpdate(BaseModel):
    serial: str | None = None
    name: str | None = None
    tag_id: str | None = None
    asset_type: str | None = None
    brand: str | None = None
    model: str | None = None
    ip_address: str | None = None
    bmc_address: str | None = None
    remark: str | None = None
    u_height: int | None = None


class AssetOut(AssetIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str


class RackOnIn(BaseModel):
    rack_id: int
    u_start: int


class AssetPage(BaseModel):
    total: int
    items: list[AssetOut]


class ImportResult(BaseModel):
    success: int
    failed: list[dict]


class AssetHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_type: str
    message: str
    created_at: datetime


class BackupInfo(BaseModel):
    name: str
    size: int
    created_at: datetime


class MessageOut(BaseModel):
    message: str


class NameIn(BaseModel):
    name: str


class RackUpdate(BaseModel):
    name: str | None = None
    u_count: int | None = None

    @field_validator("u_count")
    @classmethod
    def check_u(cls, v: int | None) -> int | None:
        if v is not None and not 1 <= v <= 60:
            raise ValueError("u_count 必须在 1-60 之间")
        return v


class TreeNode(BaseModel):
    id: int
    name: str
    type: str  # datacenter / room / group / rack
    u_count: int | None = None
    children: list["TreeNode"] = []


class RackViewOut(BaseModel):
    id: int
    name: str
    u_count: int
    group_name: str
    room_name: str
    datacenter_name: str
    assets: list[AssetOut]


class RackStats(BaseModel):
    u_count: int
    used_u: int
    free_u: int
    asset_count: int
    utilization: float
    by_type: list[dict]


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    asset_code: str
    event_type: str
    message: str
    created_at: datetime


class RoomUtilization(BaseModel):
    room: str
    datacenter: str
    racks: int
    used_u: int
    total_u: int
    utilization: float
    asset_count: int


class HomeStats(BaseModel):
    by_type: list[dict]
    by_room: list[RoomUtilization]
    status_summary: dict


class OverviewStats(BaseModel):
    datacenters: int
    rooms: int
    racks: int
    assets_on_rack: int
    assets_off_rack: int
    used_u: int
    total_u: int


# ---------- 认证 / 用户 / 审计 ----------
class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    id: int
    username: str
    display_name: str
    role: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class UserIn(BaseModel):
    username: str
    password: str
    display_name: str = ""
    role: str = "viewer"

    @field_validator("role")
    @classmethod
    def check_role(cls, v: str) -> str:
        if v not in ("admin", "operator", "viewer"):
            raise ValueError("role 必须是 admin/operator/viewer")
        return v


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None

    @field_validator("role")
    @classmethod
    def check_role(cls, v: str | None) -> str | None:
        if v is not None and v not in ("admin", "operator", "viewer"):
            raise ValueError("role 必须是 admin/operator/viewer")
        return v


class PasswordChangeIn(BaseModel):
    old_password: str
    new_password: str


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    action: str
    detail: str
    ip: str
    created_at: datetime
