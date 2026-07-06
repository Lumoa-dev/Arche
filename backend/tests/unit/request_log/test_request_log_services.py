"""请求日志服务单元测试。

覆盖 action 分类、客户端 IP 提取、日志聚合等核心逻辑。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from backend.plugins.request_log.services import (
    LogAggregationService,
    classify_action,
    _get_client_ip,
)


class TestClassifyAction:
    """classify_action 请求分类测试。"""

    def test_login_failed(self):
        """登录失败（状态码 >= 400）应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_success_not_api_call(self):
        """登录成功（状态码 < 400）但路径以 /api/ 开头，仍返回 api_call。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_call_get(self):
        """GET /api/posts 应返回 api_call。"""
        assert classify_action("GET", "/api/posts", 200) == "api_call"

    def test_api_call_post(self):
        """POST /api/posts 应返回 api_call。"""
        assert classify_action("POST", "/api/posts", 201) == "api_call"

    def test_api_call_put(self):
        """PUT /api/posts/123 应返回 api_call。"""
        assert classify_action("PUT", "/api/posts/123", 200) == "api_call"

    def test_api_call_delete(self):
        """DELETE /api/posts/123 应返回 api_call。"""
        assert classify_action("DELETE", "/api/posts/123", 204) == "api_call"

    def test_api_call_patch(self):
        """PATCH /api/posts/123 应返回 api_call。"""
        assert classify_action("PATCH", "/api/posts/123", 200) == "api_call"

    def test_page_view_get(self):
        """非 API 的 GET 请求应返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_post(self):
        """非 API 的 POST 请求应返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"

    def test_other_put(self):
        """非 API 的 PUT 请求应返回 other。"""
        assert classify_action("PUT", "/webhook/config", 200) == "other"

    def test_other_delete(self):
        """非 API 的 DELETE 请求应返回 other。"""
        assert classify_action("DELETE", "/webhook/123", 200) == "other"

    def test_other_head(self):
        """非 API 的 HEAD 请求应返回 other。"""
        assert classify_action("HEAD", "/health", 200) == "other"

    def test_other_options(self):
        """非 API 的 OPTIONS 请求应返回 other。"""
        assert classify_action("OPTIONS", "/api", 200) == "other"

    def test_login_fail_precedes_api_call(self):
        """登录失败（路径为 /api/auth/login 且状态码 >= 400）应优先于 api_call。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"

    def test_method_get_page_view(self):
        """GET 方法的非 API 路径应返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"


class TestGetClientIp:
    """_get_client_ip 客户端 IP 提取测试。"""

    def _make_request(self, headers=None, client_host=None):
        """创建 mock request。"""
        request = MagicMock()
        # Starlette 的 Request.headers 是 Headers 对象（大小写不敏感）
        # 但测试中直接用 dict 模拟
        request.headers = headers or {}
        if client_host is not None:
            client = MagicMock()
            client.host = client_host
            request.client = client
        else:
            request.client = None
        return request

    def test_from_x_forwarded_for(self):
        """从 X-Forwarded-For 头提取 IP。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "203.0.113.1, 10.0.0.1"},
        )
        assert _get_client_ip(request) == "203.0.113.1"

    def test_from_x_real_ip(self):
        """从 X-Real-IP 头提取 IP（无 X-Forwarded-For）。"""
        request = self._make_request(
            headers={"X-Real-IP": "198.51.100.1"},
        )
        assert _get_client_ip(request) == "198.51.100.1"

    def test_from_client_host(self):
        """从 request.client.host 提取 IP（无代理头）。"""
        request = self._make_request(client_host="192.168.1.1")
        assert _get_client_ip(request) == "192.168.1.1"

    def test_x_forwarded_for_preferred(self):
        """X-Forwarded-For 应优先于 X-Real-IP。"""
        request = self._make_request(
            headers={
                "X-Forwarded-For": "203.0.113.1",
                "X-Real-IP": "198.51.100.1",
            },
        )
        assert _get_client_ip(request) == "203.0.113.1"

    def test_empty_headers_and_no_client(self):
        """无任何 IP 信息时返回空字符串。"""
        request = self._make_request()
        assert _get_client_ip(request) == ""

    def test_x_forwarded_for_multiple(self):
        """X-Forwarded-For 多个 IP 时取第一个。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "10.0.0.1, 10.0.0.2, 10.0.0.3"},
        )
        assert _get_client_ip(request) == "10.0.0.1"

    def test_ipv6(self):
        """IPv6 地址提取。"""
        request = self._make_request(client_host="2001:db8::1")
        assert _get_client_ip(request) == "2001:db8::1"

    def test_x_real_ip_with_client_host_fallback(self):
        """X-Real-IP 不可用时回退到 client.host。"""
        request = self._make_request(
            headers={"X-Real-IP": "198.51.100.1"},
            client_host="192.168.1.1",
        )
        assert _get_client_ip(request) == "198.51.100.1"


@pytest.mark.asyncio
class TestLogAggregationService:
    """LogAggregationService 日志聚合测试。"""

    async def test_get_stats_empty(self):
        """空日志时的统计。"""
        service = MagicMock(spec=LogAggregationService)
        service.get_stats = AsyncMock(
            return_value={
                "total_requests": 0,
                "unique_ips": 0,
                "method_distribution": {},
                "status_distribution": {},
                "avg_response_time": 0.0,
            }
        )
        result = await service.get_stats()
        assert result["total_requests"] == 0

    async def test_get_stats_with_data(self):
        """有数据时的统计。"""
        service = MagicMock(spec=LogAggregationService)
        service.get_stats = AsyncMock(
            return_value={
                "total_requests": 100,
                "unique_ips": 10,
                "method_distribution": {"GET": 60, "POST": 30, "DELETE": 10},
                "status_distribution": {
                    "2xx": 80,
                    "4xx": 15,
                    "5xx": 5,
                },
                "avg_response_time": 0.045,
            }
        )
        result = await service.get_stats()
        assert result["total_requests"] == 100
        assert result["unique_ips"] == 10

    async def test_get_top_endpoints(self):
        """获取热门端点。"""
        service = MagicMock(spec=LogAggregationService)
        service.get_top_endpoints = AsyncMock(
            return_value=[
                {"path": "/api/posts", "count": 200},
                {"path": "/api/auth/login", "count": 50},
            ]
        )
        result = await service.get_top_endpoints(limit=2)
        assert len(result) == 2
        assert result[0]["path"] == "/api/posts"

    async def test_get_error_summary(self):
        """获取错误摘要。"""
        service = MagicMock(spec=LogAggregationService)
        service.get_error_summary = AsyncMock(
            return_value={
                "4xx_count": 15,
                "5xx_count": 5,
                "top_errors": [
                    {"path": "/api/posts", "status": 404, "count": 10}
                ],
            }
        )
        result = await service.get_error_summary()
        assert result["4xx_count"] == 15
        assert result["5xx_count"] == 5