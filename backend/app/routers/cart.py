"""
购物车接口。

【为什么存后端】bot 是独立进程，读不到浏览器的 localStorage。
购物车必须落库，bot 才能按 openid 反查并取走。

【购物车 vs 待取回队列】
  cart_items   用户"收藏"的图，长期保留
  cart_outbox  用户"这一次要取走"的图，bot 取走后即标记，不再返回

【不做校验与重发】bot 调 outbox 时后端立即标记 taken，下次不再返回。
代价：bot 崩在取走之后、发送之前，那几张图会丢。表情包场景可接受。
"""
from fastapi import APIRouter, HTTPException, Query

from ..auth import is_granted, require_edit
from ..config import settings
from ..database import get_connection
from ..models.auth import AuthResponse
from ..models.cart import (
    CartAddRequest,
    CartItem,
    CartListResponse,
    CartOutboxItem,
    CartOutboxResponse,
    CartSendRequest,
)
from fastapi import Depends
from ..thumbnail import thumbnail_path
from pathlib import Path

router = APIRouter()


def _thumb_rel(md5: str) -> str:
    """缩略图相对路径（分片镜像）：ab/cd/<md5>_thumbnail.jpg"""
    return thumbnail_path(Path(""), md5).as_posix()


@router.get("", response_model=CartListResponse)
async def list_cart(_: str = Depends(require_edit), client_id: str = Query(...)):
    """列出该 client_id 的购物车。"""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT c.md5, c.created_at, i.filename, i.tags
               FROM cart_items c
               LEFT JOIN images i ON i.md5 = c.md5
               WHERE c.client_id = ?
               ORDER BY c.created_at DESC""",
            (client_id,),
        ).fetchall()

    items = [
        CartItem(
            md5=r["md5"],
            filename=r["filename"] or "",
            tags=(r["tags"] or "").split() if r["tags"] else [],
            thumb_url=("/thumbnails/" + (r["filename"] or "")) if r["filename"] else "",
            added_at=r["created_at"],
        )
        for r in rows
    ]
    return CartListResponse(items=items, total=len(items))


@router.post("/add", response_model=AuthResponse)
async def add_to_cart(data: CartAddRequest):
    """加入购物车（幂等）。"""
    with get_connection() as conn:
        # 校验图片存在
        row = conn.execute("SELECT 1 FROM images WHERE md5 = ?", (data.md5,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="图片不存在")
        conn.execute(
            "INSERT OR IGNORE INTO cart_items (client_id, md5) VALUES (?, ?)",
            (data.client_id, data.md5),
        )
        conn.commit()
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM cart_items WHERE client_id = ?",
            (data.client_id,),
        ).fetchone()["c"]
    return AuthResponse(success=True, message=f"已加入购物车（共 {total} 张）")


@router.post("/remove", response_model=AuthResponse)
async def remove_from_cart(data: CartAddRequest):
    """移出购物车。"""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM cart_items WHERE client_id = ? AND md5 = ?",
            (data.client_id, data.md5),
        )
        conn.commit()
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM cart_items WHERE client_id = ?",
            (data.client_id,),
        ).fetchone()["c"]
    return AuthResponse(success=True, message=f"已移出购物车（余 {total} 张）")


@router.post("/clear", response_model=AuthResponse)
async def clear_cart(data: CartAddRequest):
    """清空购物车（data.md5 忽略）。"""
    with get_connection() as conn:
        conn.execute("DELETE FROM cart_items WHERE client_id = ?", (data.client_id,))
        conn.commit()
    return AuthResponse(success=True, message="购物车已清空")


@router.post("/send", response_model=AuthResponse)
async def send_cart(data: CartSendRequest):
    """把购物车推进「待取回队列」。

    之后用户私聊 bot 发送「bqbq取回」，bot 会调 /cart/outbox 取走。
    """
    with get_connection() as conn:
        if data.md5s:
            md5_list = data.md5s
        else:
            rows = conn.execute(
                "SELECT md5 FROM cart_items WHERE client_id = ?", (data.client_id,)
            ).fetchall()
            md5_list = [r["md5"] for r in rows]

        if not md5_list:
            return AuthResponse(success=False, error="购物车是空的")

        # 已在队列中的不重复加入
        conn.executemany(
            """INSERT INTO cart_outbox (client_id, md5)
               SELECT ?, ? WHERE NOT EXISTS (
                   SELECT 1 FROM cart_outbox WHERE client_id = ? AND md5 = ? AND status = 'pending'
               )""",
            [(data.client_id, m, data.client_id, m) for m in md5_list],
        )
        conn.commit()

        pending = conn.execute(
            "SELECT COUNT(*) AS c FROM cart_outbox WHERE client_id = ? AND status = 'pending'",
            (data.client_id,),
        ).fetchone()["c"]

    return AuthResponse(
        success=True,
        message=f"已加入待取回队列（共 {pending} 张），请私聊机器人发送「bqbq取回」",
    )


@router.get("/outbox", response_model=CartOutboxResponse)
async def pull_outbox(
    openid: str | None = Query(default=None, description="按 QQ openid 反查该用户的购物车"),
    client_id: str | None = Query(default=None, description="直接指定 client_id"),
    limit: int = Query(default=5, ge=1, le=20),
    _: str = Depends(require_edit),
):
    """bot 取走待发送的图片（取即标记 taken）。

    优先按 openid 反查 —— 这是 bot 唯一能拿到的身份信息。
    一个人可能在多台设备登录，会有多个 client_id，这里取并集。
    """
    if not openid and not client_id:
        raise HTTPException(status_code=400, detail="需要 openid 或 client_id")

    with get_connection() as conn:
        if openid:
            cids = [
                r["client_id"]
                for r in conn.execute(
                    "SELECT client_id FROM auth_granted_clients WHERE openid = ?", (openid,)
                ).fetchall()
            ]
            if not cids:
                return CartOutboxResponse(items=[], remaining=0, message="该 QQ 未绑定任何客户端")
        else:
            cids = [client_id]

        placeholders = ",".join("?" * len(cids))
        rows = conn.execute(
            f"""SELECT o.id, o.md5, i.filename
                FROM cart_outbox o
                LEFT JOIN images i ON i.md5 = o.md5
                WHERE o.status = 'pending' AND o.client_id IN ({placeholders})
                ORDER BY o.id
                LIMIT ?""",
            (*cids, limit),
        ).fetchall()

        if not rows:
            return CartOutboxResponse(items=[], remaining=0, message="没有待取回的表情包")

        # 取即标记
        ids = [r["id"] for r in rows]
        conn.execute(
            f"UPDATE cart_outbox SET status='taken', taken_at=CURRENT_TIMESTAMP "
            f"WHERE id IN ({','.join('?' * len(ids))})",
            ids,
        )
        conn.commit()

        remaining = conn.execute(
            f"SELECT COUNT(*) AS c FROM cart_outbox WHERE status='pending' AND client_id IN ({placeholders})",
            cids,
        ).fetchone()["c"]

    base = settings.cdn_base_url if hasattr(settings, "cdn_base_url") else ""
    items = [
        CartOutboxItem(
            md5=r["md5"],
            filename=r["filename"] or "",
            url=("/images/" + (r["filename"] or "")) if r["filename"] else "",
        )
        for r in rows
    ]
    msg = f"共 {len(items)} 张" + (f"，还剩 {remaining} 张，请再发一次" if remaining else "")
    return CartOutboxResponse(items=items, remaining=remaining, message=msg)
