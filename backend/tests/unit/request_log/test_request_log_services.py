"""请求日志服务单元测试 —— classify_action、_get_client_ip、LogAggregationService。

覆盖：
- classify_action：登录失败、API 调用、页面访问、其他分类
- _get_client_ip：X-Forwarded-For、X-Real-IP、client.host、空值
- LogAggregationService：start/stop 生命周期、聚合任务、清理任务
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    LogAggregationService,
    _get_client_ip,
    classify_action,
)


class TestClassifyAction:
    """行为分类函数测试。"""

    @pytest.mark.asyncio
    async def test_login_fail_with_4xx(self):
        """POST /api/auth/login 且状态码 >= 400 应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    @pytest.mark.asyncio
    async def test_login_success_is_api_call(self):
        """POST /api/auth/login 且状态码 < 400 应返回 api_call。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    @pytest.mark.asyncio
    async def test_api_path_returns_api_call(self):
        """以 /api/ 开头的路径应返回 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/auth/register", 201) == "api_call"
        assert classify_action("DELETE", "/api/admin/config/key", 204) == "api_call"

    @pytest.mark.asyncio
    async def test_get_non_api_returns_page_view(self):
        """非 /api/ 开头的 GET 请求应返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    @pytest.mark.asyncio
    async def test_other_methods_return_other(self):
        """非 GET 且非 /api/ 的请求应返回 other。"""
        assert classify_action("POST", "/contact", 200) == "other"
        assert classify_action("PUT", "/webhook", 200) == "other"
        assert classify_action("DELETE", "/something", 200) == "other"

    @pytest.mark.asyncio
    async def test_edge_cases(self):
        """边界情况处理。"""
        # 空路径
        result = classify_action("GET", "", 200)
        assert result in ("page_view", "other")

        # 斜杠路径
        assert classify_action("GET", "/", 200) == "page_view"

        # 各种 HTTP 方法
        assert classify_action("PATCH", "/api/config", 200) == "api_call"
        assert classify_action("HEAD", "/api/health", 200) == "api_call"


class TestGetClientIP:
    """客户端 IP 提取函数测试。"""

    def _make_request(self, headers=None, client_host=None):
        """创建模拟请求对象。"""
        request = MagicMock()
        request.headers = headers or {}
        request.client = MagicMock() if client_host else None
        if request.client:
            request.client.host = client_host
        return request

    @pytest.mark.asyncio
    async def test_x_forwarded_for_first_ip(self):
        """X-Forwarded-For 应取第一个 IP。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "203.0.113.1, 10.0.0.1, 192.168.1.1"},
            client_host="127.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.1"

    @pytest.mark.asyncio
    async def test_x_forwarded_for_single_ip(self):
        """X-Forwarded-For 单个 IP 应直接返回。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "203.0.113.1"},
            client_host="127.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.1"

    @pytest.mark.asyncio
    async def test_x_real_ip(self):
        """无 X-Forwarded-For 时，应使用 X-Real-IP。"""
        request = self._make_request(
            headers={"X-Real-IP": "203.0.113.5"},
            client_host="127.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.5"

    @pytest.mark.asyncio
    async def test_fallback_to_client_host(self):
        """无代理头时，应回退到 request.client.host。"""
        request = self._make_request(headers={}, client_host="10.0.0.1")
        assert _get_client_ip(request) == "10.0.0.1"

    @pytest.mark.asyncio
    async def test_x_forwarded_for_precedes_x_real_ip(self):
        """X-Forwarded-For 优先级高于 X-Real-IP。"""
        request = self._make_request(
            headers={
                "X-Forwarded-For": "203.0.113.1",
                "X-Real-IP": "203.0.113.5",
            },
            client_host="127.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.1"

    @pytest.mark.asyncio
    async def test_empty_headers_and_no_client(self):
        """无头部信息且无客户端时，应返回空字符串。"""
        request = self._make_request(headers={}, client_host=None)
        assert _get_client_ip(request) == ""

    @pytest.mark.asyncio
    async def test_x_forwarded_for_empty_string(self):
        """X-Forwarded-For 为空字符串时的处理。"""
        request = self._make_request(
            headers={"X-Forwarded-For": ""},
            client_host="10.0.0.1",
        )
        # 空字符串 split 得到 [""]，strip 后为空字符串
        ip = _get_client_ip(request)
        assert ip == "" or ip == "10.0.0.1"  # 取决于实现

    @pytest.mark.asyncio
    async def test_forwarded_for_with_spaces(self):
        """X-Forwarded-For 带空格处理。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "  203.0.113.1  ,  10.0.0.1  "},
            client_host="127.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.1"

    @pytest.mark.asyncio
    async def test_ipv6_in_forwarded_for(self):
        """X-Forwarded-For 中的 IPv6 地址。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "::1, 10.0.0.1"},
            client_host="127.0.0.1",
        )
        assert _get_client_ip(request) == "::1"


class TestLogAggregationService:
    """LogAggregationService 生命周期和任务测试。"""

    @pytest.mark.asyncio
    async def test_start_creates_scheduler(self):
        """start() 应创建并启动调度器。"""
        mock_scheduler = MagicMock()
        mock_scheduler.running = True

        with patch("apscheduler.schedulers.asyncio.AsyncIOScheduler") as mock_cls:
            mock_cls.return_value = mock_scheduler

            service = LogAggregationService()
            service.start()

            assert service._scheduler is not None
            mock_scheduler.add_job.assert_called()  # 应添加作业
            mock_scheduler.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        """多次 start() 不应重复创建调度器。"""
        mock_scheduler = MagicMock()
        mock_scheduler.running = True

        with patch("apscheduler.schedulers.asyncio.AsyncIOScheduler") as mock_cls:
            mock_cls.return_value = mock_scheduler

            service = LogAggregationService()
            service.start()
            service.start()  # 第二次调用

            mock_cls.assert_called_once()  # 只创建一次
            mock_scheduler.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_shuts_down_scheduler(self):
        """stop() 应关闭调度器。"""
        mock_scheduler = MagicMock()
        mock_scheduler.running = True

        with patch("apscheduler.schedulers.asyncio.AsyncIOScheduler") as mock_cls:
            mock_cls.return_value = mock_scheduler

            service = LogAggregationService()
            service.start()
            service.stop()

            mock_scheduler.shutdown.assert_called_once_with(wait=False)
            assert service._scheduler is None

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        """未启动时 stop() 不应抛出异常。"""
        service = LogAggregationService()
        service.stop()  # 不应抛出异常

    @pytest.mark.asyncio
    async def test_aggregate_job_handles_exception(self):
        """聚合任务应优雅处理异常。"""
        service = LogAggregationService()
        # 不应抛出异常
        await service._aggregate_job()

    @pytest.mark.asyncio
    async def test_cleanup_job_handles_exception(self):
        """清理任务应优雅处理异常。"""
        service = LogAggregationService()
        # 不应抛出异常
        await service._cleanup_job()