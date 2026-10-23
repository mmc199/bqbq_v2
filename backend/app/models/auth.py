"""登录鉴权相关的请求 / 响应模型。"""
from pydantic import BaseModel


class AuthRequestBody(BaseModel):
    """申请验证码 / 退出登录的请求体。"""
    client_id: str


class AuthConfirmRequest(BaseModel):
    """bot 确认验证码。"""
    code: str
    openid: str | None = None


class AuthResponse(BaseModel):
    """通用响应。"""
    success: bool
    granted: bool = False
    code: str | None = None
    expires_in: int | None = None
    message: str | None = None
    error: str | None = None


class AuthMeResponse(BaseModel):
    """登录态查询结果。"""
    granted: bool
