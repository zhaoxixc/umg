import os
import secrets


DB_HOST = os.getenv("DB_HOST", "")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "srvmgpro")
DB_PASSWORD = os.getenv("DB_PASSWORD", "srvmgpro123")
DB_NAME = os.getenv("DB_NAME", "srvmgpro")

# 未设置 SECRET_KEY 时每次重启随机生成（所有 token 失效），生产必须显式配置
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", "12"))
LOGIN_MAX_FAILS = int(os.getenv("LOGIN_MAX_FAILS", "5"))
LOGIN_LOCK_MINUTES = int(os.getenv("LOGIN_LOCK_MINUTES", "15"))

# CORS 白名单，逗号分隔；设为 * 表示不限制（仅开发环境）
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:8080,http://localhost:5173"
)

BACKUP_DIR = os.getenv("BACKUP_DIR", "./backups")
LOG_DIR = os.getenv("LOG_DIR", "./logs")


def database_url() -> str:
    if not DB_HOST:
        return "sqlite:///./srvmgpro.db"
    return (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        "?charset=utf8mb4"
    )

