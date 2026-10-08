import hashlib
import hmac
import secrets
import time

import jwt

from .config import (LOGIN_LOCK_MINUTES, LOGIN_MAX_FAILS, SECRET_KEY,
                     TOKEN_EXPIRE_HOURS)

_ITERATIONS = 200_000

# 进程内登录失败锁定（单 worker 部署；多 worker 需换 Redis）
_locks: dict[str, dict] = {}


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS)
    return f"pbkdf2${_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, hexhash = stored.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(dk.hex(), hexhash)
    except (ValueError, TypeError):
        return False


def is_locked(username: str) -> bool:
    info = _locks.get(username)
    if not info:
        return False
    if info["until"] and time.time() < info["until"]:
        return True
    if info["until"] and time.time() >= info["until"]:
        _locks.pop(username, None)
    return False


def lock_remaining_minutes(username: str) -> int:
    info = _locks.get(username) or {}
    remain = (info.get("until") or 0) - time.time()
    return max(1, int(remain // 60) + 1)


def record_fail(username: str) -> None:
    info = _locks.setdefault(username, {"fails": 0, "until": 0})
    info["fails"] += 1
    if info["fails"] >= LOGIN_MAX_FAILS:
        info["until"] = time.time() + LOGIN_LOCK_MINUTES * 60
        info["fails"] = 0


def reset_fails(username: str) -> None:
    _locks.pop(username, None)


def create_token(user) -> str:
    payload = {
        "sub": user.username,
        "uid": user.id,
        "role": user.role,
        "exp": time.time() + TOKEN_EXPIRE_HOURS * 3600,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
