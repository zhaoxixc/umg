#!/usr/bin/env bash
# 数据库恢复脚本（宿主机执行）
# 用法: ./scripts/restore.sh backups/backup_20260101_120000.sql.gz
# 注意: 恢复会覆盖当前数据库中该库的全部数据！
set -euo pipefail
cd "$(dirname "$0")/.."

FILE="${1:?用法: $0 <备份文件.sql.gz>}"
[ -f "$FILE" ] || { echo "备份文件不存在: $FILE"; exit 1; }

echo "==> 即将从 ${FILE} 恢复数据库，当前数据将被覆盖！"
read -r -p "确认恢复? 输入 yes 继续: " CONFIRM
[ "$CONFIRM" = "yes" ] || { echo "已取消"; exit 0; }

echo "==> 正在恢复..."
gunzip -c "$FILE" | docker compose exec -T db sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'

echo "==> 恢复完成，建议重启后端以刷新缓存:"
echo "    docker compose restart backend"
