#!/usr/bin/env bash
# 数据库备份脚本（宿主机执行）
# 用法: ./scripts/backup.sh [输出目录]（默认 ./backups）
set -euo pipefail
cd "$(dirname "$0")/.."

OUT_DIR="${1:-backups}"
STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$OUT_DIR"

echo "==> 正在备份数据库..."
docker compose exec -T db sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers --events "$MYSQL_DATABASE"' \
  | gzip > "${OUT_DIR}/backup_${STAMP}.sql.gz"

SIZE=$(du -h "${OUT_DIR}/backup_${STAMP}.sql.gz" | cut -f1)
echo "==> 备份完成: ${OUT_DIR}/backup_${STAMP}.sql.gz (${SIZE})"

# 可选：保留最近 N 份，删除更早的手工备份（默认保留 30 份，按需修改）
KEEP=30
ls -1t "${OUT_DIR}"/backup_*.sql.gz 2>/dev/null | tail -n +$((KEEP + 1)) | while read -r f; do
  echo "==> 清理旧备份: $f"
  rm -f "$f"
done
