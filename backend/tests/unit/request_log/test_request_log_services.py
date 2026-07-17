"""RequestLog 服务层测试。

覆盖：
- classify_action 行为分类逻辑
- _get_client_ip IP 提取
- LogAggregationService 定时任务（聚合 / TTL 清理）
- 边界条件（各种路径、方法、状态码）
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    LogAggregationService,
    classify_action,
    _get_client_ip,
)


class TestClassifyAction:
    """classify_action 行为分类测试。"""

    def test_login_fail_match(self):
        """登录失败路径 + 4xx 状态码分类为 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 400) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"

    def test_login_success_not_login_fail(self):
        """登录成功（2xx）不分类为 login_fail。"""
        result = classify_action("POST", "/api/auth/login", 200)
        assert result != "login_fail"

    def test_api_call(self):
        """API 路径分类为 api_call。"""
        assert classify_action("POST", "/api/posts", 200) == "api_call"
        assert classify_action("GET", "/api/users", 200) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"

    def test_page_view(self):
        """GET 非 API 路径分类为 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_method(self):
        """非 GET 非 API 路径分类为 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/callback", 200) == "other"

    def test_login_fail_any_method(self):
        """任何方法的登录失败都分类为 login_fail（classify_action 只看 path 和 status_code）。"""
        assert classify_action("GET", "/api/auth/login", 401) == "login_fail"
        assert classify_action("PUT", "/api/auth/login", 401) == "login_fail"


class TestGetClientIP:
    """_get_client_ip IP 提取测试。"""

    def _make_request(self, headers=None, client_host="127.0.0.1"):
        """创建 mock Request 对象。"""
        request = MagicMock()
        request.headers = headers or {}
        request.client = MagicMock()
        request.client.host = client_host
        return request

    def test_x_forwarded_for(self):
        """X-Forwarded-For 优先。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "203.0.113.1, 10.0.0.1"},
            client_host="127.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip(self):
        """X-Real-IP 次选。"""
        request = self._make_request(
            headers={"X-Real-IP": "203.0.113.5"},
            client_host="127.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.5"

    def test_fallback_to_client_host(self):
        """无代理头时回退到 client.host。"""
        request = self._make_request(headers={}, client_host="192.168.1.1")
        assert _get_client_ip(request) == "192.168.1.1"

    def test_empty_headers_and_no_client(self):
        """无代理头且无 client 时返回空字符串。"""
        request = MagicMock()
        request.headers = {}
        request.client = None
        assert _get_client_ip(request) == ""

    def test_x_forwarded_for_multiple_ips(self):
        """多个 IP 时取第一个。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "  203.0.113.1 , 10.0.0.1, 192.168.1.1"},
            client_host="127.0.0.1",
        )
        assert _get_client_ip(request) == "203.0.113.1"


class TestLogAggregationService:
    """LogAggregationService 定时任务测试。"""

    def test_start_stop_scheduler(self):
        """启动和停止调度器。"""
        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as mock_scheduler:
            service = LogAggregationService()
            service.start()
            assert service._scheduler is not None
            mock_scheduler.return_value.add_job.assert_called()

            service.stop()
            assert service._scheduler is None

    def test_start_twice_does_not_duplicate(self):
        """重复启动不重复创建调度器。"""
        with patch(
            "apscheduler.schedulers.asyncio.AsyncIOScheduler"
        ) as mock_scheduler:
            service = LogAggregationService()
            service.start()
            scheduler1 = service._scheduler
            service.start()
            assert service._scheduler is scheduler1
            mock_scheduler.assert_called_once()

    @pytest.mark.asyncio
    async def test_aggregate_job_no_error(self, db_container):
        """聚合任务在空数据库中不报错。"""
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            service = LogAggregationService()
            # 不抛异常即可
            await service._aggregate_job()

    @pytest.mark.asyncio
    async def test_cleanup_job_no_error(self, db_container):
        """TTL 清理任务在空数据库中不报错。"""
        with patch(
            "backend.plugins.request_log.services._get_session_factory",
            return_value=db_container.get("db")["session_factory"],
        ):
            service = LogAggregationService()
            await service._cleanup_job()