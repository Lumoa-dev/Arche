"""中间件和统一错误处理。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class AppError(Exception):
    """应用级错误基类。"""

    def __init__(
        self,
        message: str,
        code: str = "error",
        status_code: int = 400,
        data: dict | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.data = data or {}
        super().__init__(message)


class AuthError(AppError):
    def __init__(
        self,
        message: str = "未认证或认证已过期",
        code: str = "auth_error",
        status_code: int = 401,
    ):
        super().__init__(message, code, status_code)


class PermissionError(AppError):
    def __init__(
        self,
        message: str = "权限不足",
        code: str = "permission_denied",
        status_code: int = 403,
    ):
        super().__init__(message, code, status_code)


def error_response(
    message: str, code: str = "error", status_code: int = 400, data: dict | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "data": data or {}},
    )


def _format_validation_errors(errors: list[dict]) -> str:
    field_messages = []
    for err in errors:
        loc = err.get("loc", [])
        field_name = loc[-1] if len(loc) > 1 else loc[0] if loc else ""
        msg = err.get("msg", "校验失败")
        field_messages.append(f"{field_name}: {msg}")
    return "；".join(field_messages)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:  # noqa: ARG001
        return error_response(exc.message, exc.code, exc.status_code, exc.data)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = exc.errors()
        message = _format_validation_errors(errors)  # type: ignore[arg-type]
        return error_response(
            message, "validation_error", status.HTTP_422_UNPROCESSABLE_CONTENT
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:  # noqa: ARG001
        logger.error(
            "Unhandled exception on %s %s",
            request.method,
            request.url.path,
            exc_info=True,
        )
        return error_response(
            "内部服务器错误", "internal_error", status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def setup_cors(app: FastAPI, origins: list[str]) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全响应头中间件：为所有响应添加安全相关的 HTTP 头。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        return response


def setup_security_headers(app: FastAPI) -> None:
    """注册安全响应头中间件。"""
    app.add_middleware(SecurityHeadersMiddleware)


def get_real_ip(request: Request) -> str:
    """获取客户端真实 IP。

    优先级：X-Real-IP → X-Forwarded-For 首个 IP → request.client.host。
    在 nginx 反代环境下，request.client.host 拿到的是容器内网 IP，
    而 X-Real-IP 由 nginx 的 $remote_addr 注入，能反映真实客户端地址。
    """
    real_ip = request.headers.get("X-Real-IP", "")
    if real_ip:
        return real_ip

    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.client.host if request.client else ""


def get_current_user(request: Request) -> dict[str, Any] | None:
    """从 request.state 获取当前用户信息（由 auth 中间件注入）。"""
    return getattr(request.state, "user", None)


def require_user(request: Request) -> dict[str, Any]:
    """需要已认证用户，否则抛出 AuthError。"""
    user = get_current_user(request)
    if user is None:
        raise AuthError()
    return user


def require_level(min_level: int):
    """装饰器：要求用户等级 <= min_level（数字越小权限越高）。"""
    import functools

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            if request is None:
                raise AuthError("路由必须传入 request 参数")
            user = require_user(request)
            user_level = user.get("level", 5)
            if user_level > min_level:
                raise PermissionError(f"需要等级 <= {min_level}，当前等级 {user_level}")
            return await func(*args, **kwargs)

        return wrapper

    return decorator
