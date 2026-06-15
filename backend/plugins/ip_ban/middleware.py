"""IP 封禁插件 —— 请求拦截中间件。

每请求检查客户端 IP 是否在封禁列表中，使用 LRU 缓存加速。
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from hashlib import sha256

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class BloomFilter:
    """简易布隆过滤器（固定大小，哈希次数=3）。"""

    def __init__(self, size: int = 1_000_000):
        self._size = size
        self._bits = bytearray(size // 8 + 1)

    def _hashes(self, item: str) -> list[int]:
        h = sha256(item.encode()).hexdigest()
        return [int(h[i : i + 8], 16) % self._size for i in range(0, 24, 8)]

    def add(self, item: str) -> None:
        for pos in self._hashes(item):
            byte_idx = pos // 8
            bit_idx = pos % 8
            self._bits[byte_idx] |= 1 << bit_idx

    def contains(self, item: str) -> bool:
        for pos in self._hashes(item):
            byte_idx = pos // 8
            bit_idx = pos % 8
            if not (self._bits[byte_idx] & (1 << bit_idx)):
                return False
        return True

    def clear(self) -> None:
        self._bits = bytearray(self._size // 8 + 1)


class LRUSet:
    """固定大小的 LRU 集合（用于缓存最近检查通过的 IP）。"""

    def __init__(self, maxsize: int = 5000):
        self._maxsize = maxsize
        self._data: OrderedDict[str, None] = OrderedDict()

    def add(self, item: str) -> None:
        if item in self._data:
            self._data.move_to_end(item)
        else:
            self._data[item] = None
            if len(self._data) > self._maxsize:
                self._data.popitem(last=False)

    def contains(self, item: str) -> bool:
        if item in self._data:
            self._data.move_to_end(item)
            return True
        return False

    def remove(self, item: str) -> None:
        self._data.pop(item, None)

    def clear(self) -> None:
        self._data.clear()


class IpBanMiddleware(BaseHTTPMiddleware):
    """IP 封禁检查中间件。

    使用布隆过滤器快速判断 IP 是否可能在封禁列表中，
    再用 LRU 缓存存储已验证通过的 IP，减少数据库查询。
    """

    PUBLIC_PATHS = {  # noqa: RUF012
        "/api/auth/register",
        "/api/auth/login",
    }

    def __init__(self, app):
        super().__init__(app)
        self._bloom = BloomFilter()
        self._whitelist_cache = LRUSet(maxsize=5000)
        self._last_sync = 0.0

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in self.PUBLIC_PATHS or path.startswith(
            ("/docs", "/openapi.json", "/redoc")
        ):
            return await call_next(request)

        client_ip = request.client.host if request.client else ""

        if not client_ip:
            return await call_next(request)

        ip_ban_service = None
        try:
            container = request.app.state.container
            if container.is_available("ip_ban"):
                ip_ban_service = container.get("ip_ban")
        except Exception:
            return await call_next(request)

        if ip_ban_service is None:
            return await call_next(request)

        if self._whitelist_cache.contains(client_ip):
            return await call_next(request)

        if self._bloom.contains(client_ip):
            is_banned = await ip_ban_service.is_ip_banned(client_ip)
            if is_banned:
                logger.warning("已封禁 IP 被拦截: %s", client_ip)
                return JSONResponse(
                    status_code=403,
                    content={
                        "code": "ip_banned",
                        "message": "您的 IP 已被封禁",
                        "data": {},
                    },
                )
            self._whitelist_cache.add(client_ip)
            return await call_next(request)

        is_banned = await ip_ban_service.is_ip_banned(client_ip)
        if is_banned:
            logger.warning("已封禁 IP 被拦截: %s", client_ip)
            return JSONResponse(
                status_code=403,
                content={
                    "code": "ip_banned",
                    "message": "您的 IP 已被封禁",
                    "data": {},
                },
            )

        self._bloom.add(client_ip)
        self._whitelist_cache.add(client_ip)
        return await call_next(request)

    async def reload_cache(self, ip_ban_service) -> None:
        """重新加载布隆过滤器和缓存（封禁/解封后调用）。"""
        self._bloom.clear()
        self._whitelist_cache.clear()
        active_ips = await ip_ban_service.get_active_ip_ranges()
        for ip_range in active_ips:
            self._bloom.add(ip_range)
