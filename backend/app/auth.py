"""
登录鉴权与操作审计。

设计要点
--------
**client_id 直接作为凭据，不签发 token。**

浏览器 localStorage 里的 `client_xxxxxxxx` 是一串随机值。陌生人打开网站
也会得到自己的 client_id —— 但**它不在 `auth_granted_clients` 表里**，
所以写操作仍然被拒。安全性由「服务端的授权记录」保证，而不是 client_id
本身随机。

为什么不用 token：token 的唯一实质收益是防住"client_id 被主动拷到别的
浏览器冒用"这一个窄场景，代价却是签发、哈希存储、请求头传递、验签、
过期、清理一整套。在"防陌生访问者"这个目标下不划算。

client_id 从哪里取
-------------------
| 接口类型                  | 位置                    |
|---------------------------|-------------------------|
| 规则树 / 打标签 / 删除    | 请求体 JSON `client_id` |
| 上传（multipart 无 body） | URL query `?client_id=` |

上传接口只收文件、没有 JSON 体，client_id 无处安放，所以走 query。

管理员名单
----------
**不启用。** 任何用户私聊 bot 发验证码都能让自己的 client_id 生效。
安全性靠：站点本身有 nginx Basic 鉴权挡在外面 + 验证码 4 位一次性 +
5 分钟过期 + 每个 client_id 限次 + 用后即焚。
"""
from __future__ import annotations

import functools
import random
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Header, HTTPException, Query, Request

from .database import get_connection

# 验证码有效期（秒）
CODE_TTL_SECONDS = 300
# 同一 client_id 每小时最多申请次数
CODE_MAX_PER_HOUR = 5


# =============================================================================
#  授权检查
# =============================================================================

def is_granted(client_id: str | None) -> bool:
    """该 client_id 是否已完成 QQ 验证。"""
    if not client_id:
        return False
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM auth_granted_clients WHERE client_id = ?",
            (client_id,),
        ).fetchone()
    return row is not None


def get_openid(client_id: str | None) -> str | None:
    """反查 client_id 对应的 QQ openid（审计与购物车用）。"""
    if not client_id:
        return None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT openid FROM auth_granted_clients WHERE client_id = ?",
            (client_id,),
        ).fetchone()
    return row["openid"] if row else None


def grant(client_id: str, openid: str | None) -> None:
    """把 client_id 标记为已授权（永不过期）。"""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO auth_granted_clients (client_id, openid)
               VALUES (?, ?)
               ON CONFLICT(client_id) DO UPDATE SET openid = excluded.openid""",
            (client_id, openid),
        )
        conn.commit()


def revoke(client_id: str) -> None:
    """撤销授权（退出登录）。"""
    with get_connection() as conn:
        conn.execute("DELETE FROM auth_granted_clients WHERE client_id = ?", (client_id,))
        conn.commit()


# =============================================================================
#  FastAPI 依赖：写操作鉴权
# =============================================================================

async def require_edit(
    request: Request,
    client_id: Optional[str] = Query(default=None),
    x_client_id: Optional[str] = Header(default=None, alias="X-Client-Id"),
) -> str:
    """写接口的鉴权依赖。

    client_id 的取法优先级：
      1. URL query  `?client_id=xxx`（上传接口、bot）
      2. 请求头 `X-Client-Id`
      3. 请求体 JSON 的 `client_id` 字段（大多数网页接口）

    失败抛 401，前端据此提示用户去点 QQ 登录按钮。

    Returns:
        通过校验的 client_id。
    """
    cid = client_id or x_client_id

    if not cid:
        # 兜底：从 JSON body 里取（不改动现有接口签名的关键）
        try:
            body = await request.json()
            if isinstance(body, dict):
                cid = body.get("client_id")
        except Exception:
            cid = None

    if not cid:
        raise HTTPException(status_code=401, detail="未登录：缺少 client_id")

    if not is_granted(cid):
        raise HTTPException(status_code=401, detail="未登录：请先完成 QQ 验证")

    return cid


# =============================================================================
#  操作审计
# =============================================================================

def write_audit(
    client_id: str,
    action: str,
    target: str | None = None,
    detail: str | None = None,
) -> None:
    """写一条审计记录。

    【只记成功操作】调用方应在业务成功后再调用，避免日志被无效请求淹没。
    【失败不影响主流程】审计写失败不能让业务请求失败。
    """
    try:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO audit_log (client_id, openid, action, target, detail)
                   VALUES (?, ?, ?, ?, ?)""",
                (client_id, get_openid(client_id), action, target, detail),
            )
            conn.commit()
    except Exception as e:  # noqa: BLE001
        print(f"[Audit] 写入失败 {action}: {e}")


def audit(action: str):
    """装饰器：在写接口上标记操作名，成功返回前自动记审计。

    用法：
        @router.put("/{image_id}/tags")
        @audit("update_tags")
        async def update_image_tags(...):
            ...

    约定：被装饰函数返回前不抛异常即视为成功。
    若需要记录 target，函数可返回 dict 且包含 "audit_target" 键。
    """
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            result = await fn(*args, **kwargs)
            # 从任意位置找 client_id（body 模型 / query 参数）
            cid = None
            for v in list(kwargs.values()) + list(args):
                if isinstance(v, str) and v.startswith("client_"):
                    cid = v
                    break
                got = getattr(v, "client_id", None)
                if isinstance(got, str):
                    cid = got
                    break
            if cid:
                target = None
                if isinstance(result, dict):
                    target = result.get("audit_target")
                write_audit(cid, action, str(target) if target is not None else None)
            return result
        return wrapper
    return decorator


# =============================================================================
#  验证码
# =============================================================================

def issue_code(client_id: str) -> tuple[str | None, str | None]:
    """为 client_id 生成 4 位验证码。

    Returns:
        (code, None) 成功；(None, 错误原因) 失败（超频）。
    """
    with get_connection() as conn:
        # 限次：同一 client_id 每小时最多 5 次
        recent = conn.execute(
            """SELECT COUNT(*) AS c FROM auth_pending_codes
               WHERE client_id = ? AND created_at >= datetime('now', '-1 hour')""",
            (client_id,),
        ).fetchone()["c"]
        if recent >= CODE_MAX_PER_HOUR:
            return None, "申请过于频繁，请稍后再试"

        # 作废该 client_id 之前的未用验证码（换码即失效）
        conn.execute(
            "UPDATE auth_pending_codes SET used = 1 WHERE client_id = ? AND used = 0",
            (client_id,),
        )

        # 生成不与现有未过期码冲突的 4 位数字
        for _ in range(50):
            code = f"{random.randint(0, 9999):04d}"
            exists = conn.execute(
                "SELECT 1 FROM auth_pending_codes WHERE code = ? AND used = 0 AND expires_at > ?",
                (code, datetime.now().isoformat(sep=" ", timespec="seconds")),
            ).fetchone()
            if not exists:
                break
        else:
            return None, "验证码生成失败，请重试"

        expires = datetime.now() + timedelta(seconds=CODE_TTL_SECONDS)
        conn.execute(
            """INSERT INTO auth_pending_codes (code, client_id, expires_at)
               VALUES (?, ?, ?)""",
            (code, client_id, expires.isoformat(sep=" ", timespec="seconds")),
        )
        conn.commit()
    return code, None


def confirm_code(code: str, openid: str | None) -> tuple[bool, str]:
    """确认验证码，把对应 client_id 授权。

    Returns:
        (成功?, 提示信息)
    """
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    with get_connection() as conn:
        row = conn.execute(
            """SELECT client_id FROM auth_pending_codes
               WHERE code = ? AND used = 0 AND expires_at > ?""",
            (code, now),
        ).fetchone()
        if not row:
            return False, "验证码无效或已过期"

        client_id = row["client_id"]
        # 用后即焚
        conn.execute("UPDATE auth_pending_codes SET used = 1 WHERE code = ?", (code,))

        # 授权（永不过期）
        conn.execute(
            """INSERT INTO auth_granted_clients (client_id, openid)
               VALUES (?, ?)
               ON CONFLICT(client_id) DO UPDATE SET openid = excluded.openid""",
            (client_id, openid),
        )
        conn.commit()

    write_audit(client_id, "login", detail=f"openid={openid}")
    return True, "登录成功，请回到网页继续"


def cleanup_expired_codes() -> None:
    """清理过期的验证码与超期审计日志（挂在定时任务里调用）。"""
    try:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM auth_pending_codes WHERE expires_at < datetime('now', '-1 day')"
            )
            conn.execute(
                "DELETE FROM audit_log WHERE created_at < datetime('now', '-90 days')"
            )
            conn.commit()
    except Exception as e:  # noqa: BLE001
        print(f"[Auth] 清理过期数据失败: {e}")
