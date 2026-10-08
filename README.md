# U位资产管理系统（srvmgpro）

机房机柜 U 位资产管理系统：数据中心 → 机房 → 机柜列 → 机柜 的层级管理，42U（支持自定义 1-60U）机柜可视化、资产上架/移位/下架、空间利用率统计与上下架事件流。

## 功能

- **登录认证**：JWT 登录（默认 12h 过期），PBKDF2 密码哈希，连续失败 5 次锁定 15 分钟
- **权限管理 (RBAC)**：管理员 / 运维 / 只读 三种角色，接口级 + 按钮级双重控制
- **审计日志**：登录（含失败）、位置变更、资产上下架、用户管理等操作全留痕（操作人/IP/时间）
- **位置树**：数据中心 / 机房 / 机柜列 / 机柜 四级层级管理，支持按名称、资产编号、序列号搜索
- **机柜可视化**：设备按资产类型显示不同面板样式（服务器/交换机/路由器/防火墙/存储/其他），悬浮展示资产详情
- **资产管理**：新增、编辑、上架、移位、下架、删除；支持业务 IP、BMC 远程管理地址、备注等字段；U 位占用冲突与越界校验
- **机柜规格**：预设 42/47/48/52U，支持 1-60U 任意自定义规格
- **统计看板**：首页总览（类型分布、机房利用率 TOP、最近动态）+ 机柜级 U 位统计环图/利用率仪表/类型柱图
- **资产列表页**：分页 / 状态 / 类型 / 关键字筛选，待上架资产统一管理，单资产变更轨迹
- **Excel 导入导出**：模板下载、批量导入（逐行校验并报告错误行）、按当前筛选导出
- **备份与恢复**：应用内一键备份/恢复/下载/删除（MySQL mysqldump | SQLite 在线备份），另有宿主机脚本 `scripts/backup.sh` / `scripts/restore.sh`，备份文件落在宿主机 `./backups` 目录
- **数据库迁移**：Alembic 管理表结构版本，升级自动执行，旧库自动识别并平滑迁移

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + Element Plus + ECharts + Vite |
| 后端 | Python FastAPI + SQLAlchemy + Alembic |
| 数据库 | MySQL 8 |
| 部署 | Docker Compose（nginx + FastAPI + MySQL） |

## 快速开始（Docker Compose，推荐）

```bash
docker compose up -d --build
```

启动后访问：

- 系统界面：<http://localhost:8080>
- 后端 API：<http://localhost:8000/docs>（Swagger 文档）

首次启动自动执行数据库迁移、写入演示数据（北京数据中心 / 01号机房 / 北京一 / 15 个机柜，其中 `CPJF-S-24P` 内含 11 台在架资产）及内置账号：

| 账号 | 密码 | 角色 | 权限 |
|---|---|---|---|
| admin | admin123 | 管理员 | 全部功能：位置树管理、资产管理、用户管理、备份恢复、审计日志 |
| operator | operator123 | 运维 | 资产增删改、上架/移位/下架 |
| viewer | viewer123 | 只读 | 仅查看 |

> **生产上线前务必**：登录后立即修改默认密码，并在 `.env` 中设置固定 `SECRET_KEY`（`openssl rand -hex 32`），否则容器重启后所有登录会话失效。

```bash
docker compose down          # 停止（保留数据）
docker compose down -v       # 停止并删除数据库卷（危险）
```

## 手动构建镜像与部署

### 1. 构建镜像（可指定版本号）

```bash
# 后端镜像
docker build -t srvmgpro-backend:v1.0.0 ./backend

# 前端镜像（多阶段构建：node 编译 → nginx 运行）
docker build -t srvmgpro-frontend:v1.0.0 ./frontend

# 数据库直接使用官方镜像
docker pull mysql:8.0
```

国内网络慢时，可指定 npm/pip 镜像（Dockerfile 内已内置国内源加速与回退逻辑）。

### 2. 使用自建镜像部署

方式 A —— 修改 `docker-compose.yml` 中 `backend` / `frontend` 的 `build: ./xxx` 为：

```yaml
  backend:
    image: srvmgpro-backend:v1.0.0
    # 删除 build: ./backend
  frontend:
    image: srvmgpro-frontend:v1.0.0
    # 删除 build: ./frontend
```

然后：

```bash
docker compose up -d
```

方式 B —— 纯 `docker run`（不使用 compose，按依赖顺序）：

```bash
# 1) 网络
docker network create srvmgpro-net

# 2) 数据库
docker run -d --name srvmgpro-db --network srvmgpro-net \
  -e MYSQL_ROOT_PASSWORD=root123456 \
  -e MYSQL_DATABASE=srvmgpro -e MYSQL_USER=srvmgpro -e MYSQL_PASSWORD=srvmgpro123 \
  -e TZ=Asia/Shanghai \
  -v srvmgpro_db_data:/var/lib/mysql \
  mysql:8.0 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

# 3) 后端（等数据库就绪后启动，约 30s）
docker run -d --name srvmgpro-backend --network srvmgpro-net \
  -e DB_HOST=srvmgpro-db -e DB_PORT=3306 \
  -e DB_USER=srvmgpro -e DB_PASSWORD=srvmgpro123 -e DB_NAME=srvmgpro \
  -e SECRET_KEY=$(openssl rand -hex 32) \
  -v "$(pwd)/backups:/app/backups" -v "$(pwd)/logs:/app/logs" \
  -p 8000:8000 --restart unless-stopped \
  srvmgpro-backend:v1.0.0

# 4) 前端（nginx 反代 /api → backend:8000）
docker run -d --name srvmgpro-frontend --network srvmgpro-net \
  -p 8080:80 --restart unless-stopped \
  srvmgpro-frontend:v1.0.0
```

### 3. 离线部署（目标机无法访问外网）

```bash
# 在有网的机器上导出镜像
docker save -o srvmgpro-images.tar \
  srvmgpro-backend:v1.0.0 srvmgpro-frontend:v1.0.0 mysql:8.0

# 拷贝 srvmgpro-images.tar、docker-compose.yml、.env、scripts/ 到目标机后导入
docker load -i srvmgpro-images.tar

# 目标机上按「方式 A」修改 compose 使用镜像名后启动
docker compose up -d
```

### 4. 升级版本

```bash
docker compose build backend frontend   # 或导入新版本镜像
docker compose up -d backend frontend   # 启动时自动执行 Alembic 迁移
```

## 本地开发

后端（不配置 `DB_HOST` 时自动使用 SQLite，无需 MySQL）：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173，/api 自动代理到 8000
```

## 数据备份与恢复

**方式一：应用内（管理员）**：「资产管理 → 备份与恢复」页签，支持立即备份、下载到本地、从备份恢复、删除。恢复前会自动踢掉应用连接避免锁表，全程审计留痕。

**方式二：宿主机脚本**（适合 crontab 定时备份）：

```bash
./scripts/backup.sh                          # 备份到 ./backups/backup_时间戳.sql.gz（默认保留30份）
./scripts/restore.sh backups/xxx.sql.gz      # 交互确认后恢复，完成后建议重启后端
```

定时备份示例（每天凌晨 2 点）：

```bash
0 2 * * * cd /path/to/srvmgpro && ./scripts/backup.sh
```

> SQLite 模式（本地开发）下，应用内备份使用 SQLite 在线备份 API 生成快照文件；恢复后建议重启后端进程。

## 目录结构

```
├── docker-compose.yml
├── scripts/
│   ├── backup.sh              # 宿主机备份脚本（可挂 crontab）
│   └── restore.sh             # 宿主机恢复脚本
├── backups/                   # 备份文件（docker 卷挂载）
├── logs/                      # 应用日志（app.log，5MB×5 滚动）
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini / alembic/  # 数据库迁移
│   └── app/
│       ├── main.py            # 应用入口（迁移/日志/CORS）
│       ├── config.py          # 配置（环境变量）
│       ├── security.py        # 密码哈希、JWT、登录锁定
│       ├── deps.py            # 登录态/角色依赖、审计工具
│       ├── database.py        # 引擎/会话（带重连）
│       ├── models.py          # 用户/审计/位置/资产/事件
│       ├── schemas.py         # Pydantic 模型
│       ├── services.py        # U位校验、事件消息等公共服务
│       ├── seed.py            # 演示数据与内置账号
│       └── routers/
│           ├── auth.py        # 登录/当前用户/修改密码
│           ├── users.py       # 用户管理（admin）
│           ├── audit.py       # 审计日志查询（admin）
│           ├── stats.py       # 首页看板聚合
│           ├── backups.py     # 备份与恢复（admin）
│           ├── locations.py   # 位置树 + 层级 CRUD
│           ├── racks.py       # 机柜视图/统计/事件
│           └── assets.py      # 资产 CRUD/上下架/导入导出/轨迹
└── frontend/
    ├── Dockerfile / nginx.conf
    └── src/
        ├── views/             # 首页看板、资产视图、资产管理
        └── components/        # 位置树、机柜可视化、统计图表、事件流、备份管理等
```

## 主要接口

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/api/auth/login` | 匿名 | 登录，返回 JWT |
| GET | `/api/auth/me` | 登录 | 当前用户信息 |
| POST | `/api/auth/change-password` | 登录 | 修改本人密码 |
| GET/POST/PUT/DELETE | `/api/users` | admin | 用户管理 |
| GET | `/api/audit` | admin | 审计日志 |
| GET | `/api/stats/home` | 登录 | 首页看板聚合（类型分布/机房利用率/状态汇总） |
| GET | `/api/locations/tree?q=` | 登录 | 位置树（支持关键字过滤） |
| POST/PUT/DELETE | `/api/locations/{datacenters\|rooms\|groups\|racks}` | admin | 层级维护 |
| GET | `/api/racks/{id}/view` `stats` `events` | 登录 | 机柜视图/统计/事件 |
| GET | `/api/assets/overview` | 登录 | 全局总览统计 |
| POST | `/api/assets` | operator+ | 新增资产（可同时上架） |
| POST | `/api/assets/{id}/rack-on` | operator+ | 上架 / 移位 |
| POST | `/api/assets/{id}/rack-off` | operator+ | 下架 |
| PUT/DELETE | `/api/assets/{id}` | operator+ | 编辑 / 删除（在架不可删） |
| GET | `/api/assets?limit=&offset=&status=&asset_type=&q=` | 登录 | 分页筛选（返回 `{total, items}`） |
| GET | `/api/assets/{id}/history` | 登录 | 单资产变更轨迹 |
| GET | `/api/assets/export` `import-template` | 登录 | Excel 导出 / 导入模板下载 |
| POST | `/api/assets/import` | operator+ | Excel 批量导入（返回逐行错误） |
| GET/POST | `/api/backups` | admin | 备份列表 / 立即备份 |
| POST/GET/DELETE | `/api/backups/{name}/restore` `download` | admin | 恢复 / 下载 / 删除备份 |

## 环境变量（backend）

| 变量 | 默认 | 说明 |
|---|---|---|
| `DB_HOST` | 空 | 为空则使用本地 SQLite |
| `DB_PORT` | 3306 | MySQL 端口 |
| `DB_USER` / `DB_PASSWORD` | srvmgpro / srvmgpro123 | 数据库账号 |
| `DB_NAME` | srvmgpro | 库名 |
| `SECRET_KEY` | 随机 | JWT 签名密钥，生产必须固定（见 `.env.example`） |
| `TOKEN_EXPIRE_HOURS` | 12 | 登录有效期（小时） |
| `LOGIN_MAX_FAILS` / `LOGIN_LOCK_MINUTES` | 5 / 15 | 登录失败锁定策略 |
| `CORS_ORIGINS` | localhost 白名单 | 逗号分隔的跨域来源 |
| `BACKUP_DIR` | ./backups（容器内 /app/backups） | 备份文件目录 |
| `LOG_DIR` | ./logs（容器内 /app/logs） | 应用日志目录 |

## 更新日志

### v1.3.1（2026-10-08）
- 资产视图布局优化：左侧位置树收窄（300→236px）、右侧统计块压缩为单行三列，可视区域更大
- 右侧新增常驻「设备信息」区域：点击机柜中的设备即显示编号/序列号/机柜/U位/类型/品牌型号/业务IP/BMC/备注 + 轨迹/编辑/移位/下架快捷操作（未选中时显示占位提示，再次点击或 × 取消选中）
- 业务IP 与 BMC 地址在悬浮卡、设备信息、资产列表中独立展示
- 悬浮卡与资产对话框移除标签ID字段；编辑资产时可直接更换所在机柜/U位（换机柜自动生成移位事件、清空机柜自动下架）
- Excel 导入导出列与「设备信息」面板字段完全同步：资产编号/名称/序列号/类型/品牌/型号/高度(U)/所在机柜/起始U位/业务IP/BMC/备注（移除标签ID、状态列；机柜+U位为空即按待上架导入）
- 修复前端发版后浏览器仍加载旧页面的问题：nginx 对 index.html 返回 no-cache 头、对带 hash 的静态资源长期缓存；顶栏显示版本号便于确认当前版本
- 统计图表加高（170→210px）并优化环图标签，修复文字显示不全

### v1.3.0（2026-10-08）
- 首页改版：总览卡片 + 资产类型分布环图 + 机房空间利用率 TOP 条图 + 全局最近动态
- 机柜规格支持 1-60U 任意自定义（预设 42/47/48/52U 快捷选择）
- 资产新增字段：业务 IP 地址、BMC 远程管理地址、备注（对话框/悬浮卡/列表页/导入导出全链路支持）
- 设备外观按资产类型区分（服务器/交换机/路由器/防火墙/存储/其他）
- 数据库迁移 0002：assets 表新增 ip_address / bmc_address / remark 列

### v1.2.0（2026-10-08）
- 资产列表页（分页/筛选/待上架管理/单资产轨迹）、Excel 导入导出
- 数据备份与恢复（应用内 + 宿主机脚本）
- Alembic 迁移、访问日志落地、CORS 收紧、compose 健康检查

### v1.1.0（2026-10-04）
- JWT 登录 + RBAC（管理员/运维/只读）+ 审计日志 + 用户管理
- 位置树管理（增删改 + 删除保护）、机柜 U 数修改保护

### v1.0.0（2026-10-04）
- 首个可用版本：位置树、42U 机柜可视化、资产管理、统计看板、事件流、Docker Compose 部署
