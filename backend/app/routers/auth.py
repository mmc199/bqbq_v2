"""
登录鉴权接口。

流程
----
① 网页点「QQ 登录」→ POST /auth/request { client_id }
      后端生成 4 位验证码，5 分钟有效，返回给网页展示
② 用户私聊 bot 发送「bqbq登录 4821」
      bot → POST /auth/confirm { code, openid }
      后端校验验证码有效 → 把该 client_id 写入 auth_granted_clients（永不过期）
③ 网页轮询 GET /auth/me?client_id=xxx → 得到 granted=true
      之后所有写请求带 client_id 即可，鉴权由 require_edit 完成

【不校验管理员】任何用户都能让验证码生效。
安全性靠：站点本身有 nginx Basic 鉴权 + 验证码 4 位一次性 + 5 分钟 +
每个 client_id 每小时限 5 次 + 用后即焚。
"""
from fastapi import APIRouter, HTTPException

from ..auth import (
    CODE_TTL_SECONDS,
    confirm_code,
    is_granted,
    issue_code,
    revoke,
)
from ..models.auth import AuthConfirmRequest, AuthMeResponse, AuthRequestBody, AuthResponse

router = APIRouter()


@router.post("/request", response_model=AuthResponse)
async def request_code(data: AuthRequestBody):
    """申请验证码。"""
    if not data.client_id or not data.client_id.startswith("client_"):
        raise HTTPException(status_code=400, detail="client_id 格式不正确")

    if is_granted(data.client_id):
        return AuthResponse(
            success=True,
            granted=True,
            message="该客户端已登录，无需再次验证",
        )

    code, err = issue_code(data.client_id)
    if err:
        return AuthResponse(success=False, granted=False, error=err)

    return AuthResponse(
        success=True,
        granted=False,
        code=code,
        expires_in=CODE_TTL_SECONDS,
        message="请在 QQ 私聊机器人发送指令完成验证",
    )


@router.post("/confirm", response_model=AuthResponse)
async def confirm(data: AuthConfirmRequest):
    """确认验证码（bot 调用）。

    不做调用方鉴权 —— bot 与后端同机（127.0.0.1），且验证码本身即凭证。
    """
    code = (data.code or "").strip()
    if not code:
        return AuthResponse(success=False, error="缺少验证码")

    ok, msg = confirm_code(code, data.openid)
    if not ok:
        return AuthResponse(success=False, error=msg)

    return AuthResponse(success=True, granted=True, message=msg)


@router.get("/me", response_model=AuthMeResponse)
async def me(client_id: str):
    """查询当前 client_id 的登录态（前端轮询用）。"""
    return AuthMeResponse(granted=is_granted(client_id))


@router.post("/logout", response_model=AuthResponse)
async def logout(data: AuthRequestBody):
    """退出登录（撤销该 client_id 的授权）。"""
    revoke(data.client_id)
    return AuthResponse(success=True, granted=False, message="已退出登录")
