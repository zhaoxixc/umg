"""后端接口冒烟测试（使用 sqlite，不依赖 MySQL）"""
import os
import sys

os.environ.pop("DB_HOST", None)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

with TestClient(app) as c:
    # ---------- 认证 ----------
    r = c.get("/api/locations/tree")
    assert r.status_code == 401, "未登录应 401"

    r = c.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 400
    tok = c.post("/api/auth/login",
                 json={"username": "admin", "password": "admin123"}).json()
    assert tok["role"] == "admin" and tok["access_token"]
    AH = {"Authorization": f"Bearer {tok['access_token']}"}
    me = c.get("/api/auth/me", headers=AH).json()
    assert me["username"] == "admin"

    vtok = c.post("/api/auth/login",
                  json={"username": "viewer", "password": "viewer123"}).json()
    VH = {"Authorization": f"Bearer {vtok['access_token']}"}
    otok = c.post("/api/auth/login",
                  json={"username": "operator", "password": "operator123"}).json()
    OH = {"Authorization": f"Bearer {otok['access_token']}"}

    # viewer 只读
    assert c.get("/api/locations/tree", headers=VH).status_code == 200
    assert c.post("/api/assets", headers=VH, json={
        "code": "X", "name": "X"}).status_code == 403
    # operator 不能动位置树 / 用户 / 审计
    assert c.post("/api/locations/datacenters", headers=OH,
                  json={"name": "nope"}).status_code == 403
    assert c.get("/api/users", headers=OH).status_code == 403
    assert c.get("/api/audit", headers=OH).status_code == 403
    assert c.get("/api/users", headers=VH).status_code == 403

    # 登录失败锁定（用临时账号，避免影响 admin）
    c.post("/api/users", headers=AH, json={
        "username": "locktest", "password": "locktest1", "role": "viewer"})
    for _ in range(5):
        r = c.post("/api/auth/login",
                   json={"username": "locktest", "password": "bad"})
        assert r.status_code == 400
    r = c.post("/api/auth/login",
               json={"username": "locktest", "password": "locktest1"})
    assert r.status_code == 400 and "锁定" in r.json()["detail"]

    # 健康检查 + 种子数据
    assert c.get("/api/health").json() == {"status": "ok"}
    tree = c.get("/api/locations/tree", headers=AH).json()
    assert tree[0]["name"] == "北京数据中心", tree
    room = tree[0]["children"][0]
    group = room["children"][0]
    racks = {r["name"]: r["id"] for r in group["children"]}
    assert "CPJF-S-24P" in racks and "BJRM01-0403" in racks, racks
    rack_id = racks["CPJF-S-24P"]

    # 机柜视图
    view = c.get(f"/api/racks/{rack_id}/view", headers=AH).json()
    assert view["u_count"] == 42 and len(view["assets"]) == 11, view
    u34 = [a for a in view["assets"] if a["u_start"] == 34][0]
    assert u34["name"] == "华为S5720-28P-LI交换机" and u34["tag_id"] == "6700D42F"

    # 统计：14U 已用 / 28U 空闲 / 33.33%
    st = c.get(f"/api/racks/{rack_id}/stats", headers=AH).json()
    assert st["used_u"] == 14 and st["free_u"] == 28, st
    assert st["asset_count"] == 11 and st["utilization"] == 33.33, st
    types = {t["name"]: t["count"] for t in st["by_type"]}
    assert types == {"服务器": 9, "交换机": 2}, types

    # 事件
    ev = c.get(f"/api/racks/{rack_id}/events", headers=AH).json()
    assert len(ev) >= 12 and ev[0]["message"].endswith("上架")

    # 搜索
    tree2 = c.get("/api/locations/tree", headers=AH, params={"q": "CPJF-S-24P"}).json()
    assert len(tree2[0]["children"][0]["children"]) == 1

    # 资产 CRUD + 上下架
    new = c.post("/api/assets", headers=AH, json={
        "code": "TEST001", "name": "测试服务器", "serial": "SNTEST001",
        "asset_type": "服务器", "rack_id": rack_id, "u_start": 40, "u_height": 1,
    })
    assert new.status_code == 200, new.text
    aid = new.json()["id"]
    st = c.get(f"/api/racks/{rack_id}/stats", headers=AH).json()
    assert st["used_u"] == 15 and st["utilization"] == 35.71, st

    # 冲突校验：U34 已被占用
    dup = c.post("/api/assets", headers=AH, json={
        "code": "TEST002", "name": "冲突资产", "rack_id": rack_id, "u_start": 34,
    })
    assert dup.status_code == 400

    # 移位
    mv = c.post(f"/api/assets/{aid}/rack-on", headers=AH, json={"rack_id": rack_id, "u_start": 38})
    assert mv.status_code == 200 and mv.json()["u_start"] == 38, mv.text

    # 下架 -> 变为待上架
    off = c.post(f"/api/assets/{aid}/rack-off", headers=AH)
    assert off.status_code == 200 and off.json()["status"] == "off_rack"
    # 下架后可删除
    assert c.delete(f"/api/assets/{aid}", headers=AH).status_code == 200

    # 编辑
    e = c.put(f"/api/assets/{u34['id']}", headers=AH, json={"brand": "华为技术"})
    assert e.status_code == 200 and e.json()["brand"] == "华为技术"

    # 新字段：IP / BMC / 备注
    n = c.post("/api/assets", headers=AH, json={
        "code": "NETFIELD-01", "name": "字段验证服务器", "asset_type": "服务器",
        "ip_address": "10.0.1.50", "bmc_address": "10.0.100.50", "remark": "核心业务",
    }).json()
    assert n["ip_address"] == "10.0.1.50" and n["bmc_address"] == "10.0.100.50"
    assert n["remark"] == "核心业务"
    e2 = c.put(f"/api/assets/{n['id']}", headers=AH, json={"ip_address": "10.0.1.51"})
    assert e2.json()["ip_address"] == "10.0.1.51"
    c.post(f"/api/assets/{n['id']}/rack-off", headers=AH)
    c.delete(f"/api/assets/{n['id']}", headers=AH)

    # ---------- 首页看板聚合 ----------
    hs = c.get("/api/stats/home", headers=AH).json()
    types = {t["name"]: t["count"] for t in hs["by_type"]}
    assert "服务器" in types, hs
    assert hs["status_summary"]["on_rack"] >= 11
    assert len(hs["by_room"]) >= 1
    r0 = hs["by_room"][0]
    assert {"room", "datacenter", "racks", "used_u", "total_u", "utilization", "asset_count"} <= set(r0)
    assert 0 <= r0["utilization"] <= 100
    utils = [r["utilization"] for r in hs["by_room"]]
    assert utils == sorted(utils, reverse=True), "机房按利用率降序"

    # 总览
    ov = c.get("/api/assets/overview", headers=AH).json()
    assert ov["racks"] == 15 and ov["assets_on_rack"] == 11 and ov["total_u"] > 0, ov

    # 位置 CRUD
    dc = c.post("/api/locations/datacenters", headers=AH, json={"name": "测试DC"}).json()
    room2 = c.post("/api/locations/rooms", headers=AH,
                   json={"name": "测试机房", "datacenter_id": dc["id"]}).json()
    g2 = c.post("/api/locations/groups", headers=AH,
                json={"name": "测试列", "room_id": room2["id"]}).json()
    r2 = c.post("/api/locations/racks", headers=AH,
                json={"name": "TEST-R01", "group_id": g2["id"], "u_count": 47}).json()
    assert r2["u_count"] == 47

    # 重命名 / 修改 U 数
    assert c.put(f"/api/locations/datacenters/{dc['id']}", headers=AH,
                 json={"name": "测试DC改"}).json()["name"] == "测试DC改"
    dup = c.put(f"/api/locations/datacenters/{dc['id']}", headers=AH, json={"name": "北京数据中心"})
    assert dup.status_code == 400  # 名称重复
    r3 = c.put(f"/api/locations/racks/{r2['id']}", headers=AH,
               json={"name": "TEST-R01X", "u_count": 52}).json()
    assert r3["name"] == "TEST-R01X" and r3["u_count"] == 52

    # U 数不能小于已占用最高 U 位：在 TEST-R01X 的 50U 放一台 2U 资产后，改 47U 应失败
    t = c.post("/api/assets", headers=AH, json={
        "code": "TEST003", "name": "占位服务器", "rack_id": r2["id"],
        "u_start": 50, "u_height": 2,
    })
    assert t.status_code == 200, t.text
    bad = c.put(f"/api/locations/racks/{r2['id']}", headers=AH, json={"u_count": 47})
    assert bad.status_code == 400

    # 删除保护：下有在架资产的机柜/机柜列/机房/数据中心均不可删
    assert c.delete(f"/api/locations/racks/{r2['id']}", headers=AH).status_code == 400
    assert c.delete(f"/api/locations/groups/{g2['id']}", headers=AH).status_code == 400
    assert c.delete(f"/api/locations/rooms/{room2['id']}", headers=AH).status_code == 400
    assert c.delete(f"/api/locations/datacenters/{dc['id']}", headers=AH).status_code == 400
    # 下架后整条链路可删
    assert c.post(f"/api/assets/{t.json()['id']}/rack-off", headers=AH).status_code == 200
    assert c.delete(f"/api/assets/{t.json()['id']}", headers=AH).status_code == 200
    assert c.delete(f"/api/locations/racks/{r2['id']}",
                    headers=AH).json()["message"] == "已删除"
    assert c.delete(f"/api/locations/groups/{g2['id']}",
                    headers=AH).json()["message"] == "已删除"
    assert c.delete(f"/api/locations/rooms/{room2['id']}",
                    headers=AH).json()["message"] == "已删除"
    assert c.delete(f"/api/locations/datacenters/{dc['id']}",
                    headers=AH).json()["message"] == "已删除"

    # 审计日志（admin）
    audit = c.get("/api/audit", headers=AH).json()
    actions = {a["action"] for a in audit}
    assert "login" in actions and "login_failed" in actions and "asset_create" in actions, actions
    assert any(a["username"] == "admin" for a in audit)

    # 用户管理
    ul = c.get("/api/users", headers=AH).json()
    assert len(ul) >= 4
    uid = [u["id"] for u in ul if u["username"] == "locktest"][0]
    assert c.put(f"/api/users/{uid}", headers=AH,
                 json={"role": "operator"}).json()["role"] == "operator"
    assert c.put(f"/api/users/{uid}", headers=AH,
                 json={"password": "newpass66"}).status_code == 200
    assert c.post("/api/auth/login",
                  json={"username": "locktest", "password": "newpass66"}).status_code == 400  # 仍锁定
    assert c.delete(f"/api/users/{uid}", headers=AH).json()["message"] == "已删除"
    # 不能删自己 / 不能禁用自己 / 最后一个管理员保护
    aid_admin = me["id"]
    assert c.delete(f"/api/users/{aid_admin}", headers=AH).status_code == 400
    assert c.put(f"/api/users/{aid_admin}", headers=AH,
                 json={"is_active": False}).status_code == 400

    # 修改自己密码
    r = c.post("/api/auth/change-password", headers=AH,
               json={"old_password": "admin123", "new_password": "admin456"})
    assert r.status_code == 200
    tok2 = c.post("/api/auth/login",
                  json={"username": "admin", "password": "admin456"}).json()
    assert tok2["access_token"]
    # 改回默认，便于重复测试
    c.post("/api/auth/change-password",
           headers={"Authorization": f"Bearer {tok2['access_token']}"},
           json={"old_password": "admin456", "new_password": "admin123"})

    # ---------- 资产列表分页 ----------
    page = c.get("/api/assets", headers=AH, params={"limit": 5, "offset": 0}).json()
    assert page["total"] >= 12 and len(page["items"]) == 5, page["total"]
    page2 = c.get("/api/assets", headers=AH,
                  params={"status": "off_rack", "limit": 50}).json()
    assert page2["total"] >= 2  # 种子里有 2 台待上架
    assert all(i["status"] == "off_rack" for i in page2["items"])

    # ---------- 单资产轨迹 ----------
    hist = c.get(f"/api/assets/{u34['id']}/history", headers=AH).json()
    assert isinstance(hist, list)

    # ---------- Excel 导出 / 模板 ----------
    r = c.get("/api/assets/export", headers=AH)
    assert r.status_code == 200 and "spreadsheetml" in r.headers["content-type"]
    r = c.get("/api/assets/import-template", headers=AH)
    assert r.status_code == 200

    # ---------- Excel 导入 ----------
    import io
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["资产编号", "资产名称", "资产序列号", "资产类型",
               "资产品牌", "资产型号", "资产高度(U)", "所在机柜", "起始U位",
               "业务IP地址", "BMC管理地址", "备注"])
    ws.append(["IMP0001", "导入服务器", "SNIMP1", "服务器", "华为", "2288H", 2, "", "",
               "10.1.1.11", "10.1.100.11", "导入备注"])
    ws.append(["IMP0002", "导入交换机", "SNIMP2", "交换机", "华为", "S5735", 1, "CPJF-S-24P", 36,
               "10.1.1.12", "", ""])
    ws.append(["IMP0001", "重复编号", "", "服务器", "", "", 1, "", "", "", "", ""])
    ws.append(["IMP0004", "机柜不存在", "", "服务器", "", "", 1, "NO-SUCH-RACK", 5, "", "", ""])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    r = c.post("/api/assets/import", headers=AH,
               files={"file": ("import.xlsx", buf,
                      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert r.status_code == 200, r.text
    imp = r.json()
    assert imp["success"] == 2, imp
    assert len(imp["failed"]) == 2 and {f["row"] for f in imp["failed"]} == {4, 5}, imp
    imp_assets = c.get("/api/assets", headers=AH, params={"q": "IMP0002"}).json()
    assert imp_assets["items"][0]["status"] == "on_rack"
    assert imp_assets["items"][0]["rack_id"] == rack_id
    imp1 = c.get("/api/assets", headers=AH, params={"q": "IMP0001"}).json()["items"][0]
    assert imp1["ip_address"] == "10.1.1.11" and imp1["bmc_address"] == "10.1.100.11"
    assert imp1["remark"] == "导入备注"

    # 轨迹应有上架记录
    hist = c.get(f"/api/assets/{imp_assets['items'][0]['id']}/history", headers=AH).json()
    assert any(e["event_type"] == "rack_on" for e in hist)

    # ---------- 备份与恢复 ----------
    assert c.get("/api/backups", headers=OH).status_code == 403  # operator 禁止
    r = c.post("/api/backups", headers=AH)
    assert r.status_code == 200, r.text
    bk = r.json()
    assert bk["name"].endswith(".db") and bk["size"] > 0, bk
    lst = c.get("/api/backups", headers=AH).json()
    assert any(b["name"] == bk["name"] for b in lst)
    r = c.get(f"/api/backups/{bk['name']}/download", headers=AH)
    assert r.status_code == 200 and len(r.content) == bk["size"]
    assert c.post(f"/api/backups/{bk['name']}/restore", headers=AH).status_code == 200
    assert c.get("/api/health").json() == {"status": "ok"}  # 恢复后服务正常
    assert c.delete(f"/api/backups/{bk['name']}", headers=AH).json()["message"] == "已删除"
    # 路径穿越防护
    assert c.get("/api/backups/..%2Fmain.py/download", headers=AH).status_code in (400, 404)

print("ALL BACKEND TESTS PASSED")
