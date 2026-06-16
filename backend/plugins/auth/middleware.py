"""认证插件 —— JWT 认证中间件。

从请求头提取 Bearer token，解析后注入 request.state.user。
对公开路由（/api/auth/register, /api/auth/login）跳过认证。
同时自动刷新在线会话的 last_seen_at（隐式心跳）。
"""

from __future__ import annotations

import logging

import jwt
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT 认证中间件：解析 token 并注入 request.state.user。"""

    # 不需要认证的公开路由（仅注册和登录等身份端点）
    PUBLIC_PATHS = {  # noqa: RUF012
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/refresh",
        "/api/ping",
    }

    # 博客公开 GET 路由前缀（列出具体前缀，含列表页 /api/blog/posts）
    BLOG_PUBLIC_PREFIXES = (
        "/api/blog/posts",
        "/api/blog/tags",
    )

    # FastAPI 内置路由（/docs, /openapi.json 等）跳过认证
    INTERNAL_PREFIXES = ("/docs", "/openapi.json", "/redoc")

    def __init__(self, app, secret_key: str):
        super().__init__(app)
        self.secret_key = secret_key

    def _refresh_session(self, request: Request, user_id: str) -> None:
        """刷新用户的会话时间（隐式心跳）。"""
        try:
            container = request.app.state.container
            if container.is_available("session_tracker"):
                tracker = container.get("session_tracker")
                tracker.refresh(user_id)
        except Exception:
            pass

    async def _handle_mock_token(
        self, request: Request, call_next, token: str
    ) -> Response:
        """处理开发模式的 mock token，构造虚拟用户信息。"""
        # token 格式: mock-token-{role}-{timestamp}
        parts = token.split("-")
        role = parts[2] if len(parts) > 2 else "user"

        mock_users = {
            "admin": {
                "id": "00000000-0000-0000-0000-000000000001",
                "email": "admin@example.com",
                "username": "admin",
                "level": 0,
                "blog_quality_level": 5,
            },
            "user": {
                "id": "00000000-0000-0000-0000-000000000002",
                "email": "user@example.com",
                "username": "user",
                "level": 1,
                "blog_quality_level": 3,
            },
            "guest": {
                "id": "00000000-0000-0000-0000-000000000003",
                "email": "",
                "username": "guest",
                "level": 5,
                "blog_quality_level": 0,
            },
        }

        user = mock_users.get(role, mock_users["user"])
        request.state.user = user
        self._refresh_session(request, user["id"])  # type: ignore[arg-type]
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(
                "Mock token handler 未捕获异常: %s %s - %s",
                request.method,
                request.url.path,
                str(e),
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "code": "internal_error",
                    "message": "内部服务器错误",
                    "data": {},
                },
            )

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        method = request.method

        try:
            # 公开路由和 FastAPI 内置路由直接放行
            if path in self.PUBLIC_PATHS or path.startswith(self.INTERNAL_PREFIXES):
                return await call_next(request)

            # 博客公开 GET 路由：允许未认证访问，但如果有 token 就解析注入用户信息
            if method == "GET" and path.startswith(self.BLOG_PUBLIC_PREFIXES):
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    # 开发模式：接受 mock-token-*
                    if token.startswith("mock-token-"):
                        return await self._handle_mock_token(request, call_next, token)
                    try:
                        payload = jwt.decode(
                            token, self.secret_key, algorithms=["HS256"]
                        )
                        request.state.user = {
                            "id": payload["sub"],
                            "email": payload.get("email", ""),
                            "username": payload.get("username", ""),
                            "level": payload["level"],
                            "blog_quality_level": payload.get("blog_quality_level", 0),
                        }
                    except Exception:
                        pass  # token 无效，当作匿名用户
                    else:
                        self._refresh_session(request, payload["sub"])
                return await call_next(request)

            # 提取 Authorization header
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={
                        "code": "auth_error",
                        "message": "缺少认证信息",
                        "data": {},
                    },
                )

            token = auth_header[7:]  # 去掉 "Bearer " 前缀

            # 开发模式：接受 mock-token-* 作为测试用登录令牌
            if token.startswith("mock-token-"):
                return await self._handle_mock_token(request, call_next, token)

            # 解析 token
            try:
                payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                return JSONResponse(
                    status_code=401,
                    content={
                        "code": "token_expired",
                        "message": "Token 已过期",
                        "data": {},
                    },
                )
            except jwt.InvalidTokenError:
                return JSONResponse(
                    status_code=401,
                    content={
                        "code": "invalid_token",
                        "message": "无效 Token",
                        "data": {},
                    },
                )

            # 检查 token 是否已被登出（黑名单）
            jti = payload.get("jti")
            if jti:
                try:
                    auth_service = request.app.state.container.get("auth")
                    if auth_service.is_token_blacklisted(jti):
                        return JSONResponse(
                            status_code=401,
                            content={
                                "code": "auth_error",
                                "message": "Token 已失效，请重新登录",
                                "data": {},
                            },
                        )
                except Exception:
                    pass  # 黑名单检查失败时放行，避免影响正常请求

            # 注入用户信息到 request.state
            request.state.user = {
                "id": payload["sub"],
                "email": payload.get("email", ""),
                "username": payload.get("username", ""),
                "level": payload["level"],
                "blog_quality_level": payload.get("blog_quality_level", 0),
            }

            # 刷新在线会话（隐式心跳）
            self._refresh_session(request, payload["sub"])

            return await call_next(request)
        except Exception as e:
            logger.error(
                "AuthMiddleware 未捕获异常: %s %s - %s",
                request.method,
                request.url.path,
                str(e),
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "code": "internal_error",
                    "message": "内部服务器错误",
                    "data": {},
                },
            )
