from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .models import Asset, AssetEvent, DataCenter, Rack, Room, RackGroup, User
from .security import hash_password

DEMO_USERS = [
    ("admin", "admin123", "系统管理员", "admin"),
    ("operator", "operator123", "运维工程师", "operator"),
    ("viewer", "viewer123", "访客", "viewer"),
]


def seed_users(db: Session) -> None:
    if db.query(User).count():
        return
    for username, password, display_name, role in DEMO_USERS:
        db.add(User(username=username, password_hash=hash_password(password),
                    display_name=display_name, role=role))
    db.commit()


def seed_if_empty(db: Session) -> None:
    if db.query(DataCenter).count():
        return

    dc = DataCenter(name="北京数据中心")
    room = Room(name="北京数据中心01号机房", datacenter=dc)
    g1 = RackGroup(name="北京一", room=room)
    db.add_all([dc, room, g1])
    db.flush()

    rack_names = [
        "BJRM01-0403", "BJRM01-0402", "BJRM01-0404", "BJRM01-0405",
        "BJRM01-0101", "CPJF-S-24P", "CPJF-Z-40P", "BJRM01-0102",
        "BJRM01-0103", "BJRM01-0104", "BJRM01-0105", "BJRM01-0106",
        "BJRM01-0201", "BJRM01-0202", "BJRM01-0203",
    ]
    racks = {name: Rack(name=name, group=g1,
                        u_count=42 if name == "CPJF-S-24P" else 47)
             for name in rack_names}
    db.add_all(racks.values())
    db.flush()

    main = racks["CPJF-S-24P"]
    now = datetime.now()

    def asset(code, serial, name, tag, a_type, brand, model,
              u_start=None, u_height=1):
        return Asset(
            code=code, serial=serial, name=name, tag_id=tag,
            asset_type=a_type, brand=brand, model=model,
            rack_id=main.id if u_start else None,
            u_start=u_start, u_height=u_height,
            status="on_rack" if u_start else "off_rack",
        )

    assets = [
        # 2 台交换机 (2U)
        asset("2026050610008", "SN26438097942", "华为S5720-28P-LI交换机",
              "6700D42F", "交换机", "华为", "S5720-28P-LI-AC", 34),
        asset("2026050610009", "SN26438097943", "华为CE6857交换机",
              "6700D430", "交换机", "华为", "CE6857F-48S6CQ", 33),
        # 9 台服务器 (3×2U + 6×1U = 12U)
        asset("SM2026032701", "SN26469889431", "华为2288H V5服务器",
              "5A10B301", "服务器", "华为", "2288H V5", 30, 2),
        asset("SM2026032702", "SN26469889432", "戴尔R740服务器",
              "5A10B302", "服务器", "戴尔", "PowerEdge R740", 28, 2),
        asset("SM2026032703", "SN26469889438", "浪潮NF5280M5服务器",
              "5A10B303", "服务器", "浪潮", "NF5280M5", 25, 2),
        asset("SM2026032704", "SN26469889441", "华为2288H V5服务器",
              "5A10B304", "服务器", "华为", "2288H V5", 23),
        asset("SM2026032705", "SN26469889442", "戴尔R640服务器",
              "5A10B305", "服务器", "戴尔", "PowerEdge R640", 22),
        asset("SM2026032706", "SN26469889443", "浪潮NF5280M5服务器",
              "5A10B306", "服务器", "浪潮", "NF5280M5", 20),
        asset("SM2026032707", "SN26469889444", "华为2288H V5服务器",
              "5A10B307", "服务器", "华为", "2288H V5", 19),
        asset("SM2026032708", "SN26469889445", "戴尔R640服务器",
              "5A10B308", "服务器", "戴尔", "PowerEdge R640", 15),
        asset("SM2026032709", "SN26469889446", "浪潮NF5270M6服务器",
              "5A10B309", "服务器", "浪潮", "NF5270M6", 14),
        # 2 台待上架资产
        asset("SM2026041101", "SN26471120001", "华为S5735交换机",
              "6700D50A", "交换机", "华为", "S5735-L24T4S-A"),
        asset("SM2026041102", "SN26471120002", "戴尔R750服务器",
              "5A10B400", "服务器", "戴尔", "PowerEdge R750"),
    ]
    db.add_all(assets)
    db.flush()

    def ev(asset, action, minutes_ago, etype):
        db.add(AssetEvent(
            asset_id=asset.id, asset_code=asset.code, event_type=etype,
            message=(f"数据中心:北京数据中心|机房:北京数据中心01号机房|机柜:{main.name}|"
                     f"资产编号:{asset.code},资产序列号:{asset.serial}|"
                     f"U位:{asset.u_start}U|{action}"),
            created_at=now - timedelta(minutes=minutes_ago),
        ))

    ev(assets[0], "上架", 60 * 24 * 9, "rack_on")
    ev(assets[1], "上架", 60 * 24 * 9 - 5, "rack_on")
    ev(assets[2], "上架", 60 * 24 * 7, "rack_on")
    ev(assets[3], "上架", 60 * 24 * 5, "rack_on")
    ev(assets[4], "上架", 60 * 24 * 5 - 10, "rack_on")
    ev(assets[5], "上架", 60 * 24 * 3, "rack_on")
    ev(assets[5], "移位", 60 * 24 * 2, "move")
    ev(assets[6], "上架", 60 * 30, "rack_on")
    ev(assets[7], "上架", 60 * 28, "rack_on")
    ev(assets[8], "上架", 60 * 26, "rack_on")
    ev(assets[9], "上架", 60 * 24, "rack_on")
    ev(assets[10], "上架", 60 * 20, "rack_on")
    ev(assets[11], "上架", 60 * 18, "rack_on")
    db.commit()
