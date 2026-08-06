"""RequestLog 服务单元测试。

测试原则：
- 纯函数用参数化测试验证
- 异步写入逻辑用 mock 隔离
- 每个测试独立，不依赖执行顺序
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from backend.plugins.request_log.services import (
    LogAggregationService,
    _get_client_ip,
    classify_action,
)
from backend.plugins.request_log.services import (
    _SKIP_PATHS,
    _SKIP_PREFIXES,
)


# =============================================================================
# classify_action 测试
# =============================================================================


class TestClassifyAction:
    """classify_action 行为分类测试。"""

    def test_login_fail_path_with_4xx_status(self):
        """登录路径且状态码 >= 400 应返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 500) == "login_fail"

    def test_login_path_with_success_status(self):
        """登录路径且状态码 < 400 应返回 api_call。"""
        assert classify_action("POST", "/api/auth/login", 200) == "api_call"

    def test_api_prefix_path(self):
        """/api/ 前缀路径应返回 api_call。"""
        assert classify_action("GET", "/api/posts", 200) == "api_call"
        assert classify_action("POST", "/api/posts", 201) == "api_call"
        assert classify_action("DELETE", "/api/posts/1", 204) == "api_call"

    def test_get_non_api_path(self):
        """GET 非 API 路径应返回 page_view。"""
        assert classify_action("GET", "/", 200) == "page_view"
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/contact", 200) == "page_view"

    def test_other_methods(self):
        """非 GET 且非 API 路径应返回 other。"""
        assert classify_action("POST", "/webhook", 200) == "other"
        assert classify_action("PUT", "/callback", 200) == "other"
        assert classify_action("DELETE", "/resource/1", 200) == "other"


# =============================================================================
# _get_client_ip 测试
# =============================================================================


class TestGetClientIp:
    """_get_client_ip IP 提取测试。"""

    def _make_request(self, headers: dict | None = None, client_host: str | None = None):
        scope = {
            "type": "http",
            "headers": [],
        }
        if client_host:
            scope["client"] = (client_host, 12345)
        request = Request(scope)
        if headers:
            for key, value in headers.items():
                request.headers._list.append((key.lower().encode(), value.encode()))
        return request

    def test_forwarded_for_returns_first_ip(self):
        """X-Forwarded-For 应返回第一个 IP。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "10.0.0.1, 192.168.1.1, 172.16.0.1"}
        )
        assert _get_client_ip(request) == "10.0.0.1"

    def test_real_ip_when_no_forwarded(self):
        """无 X-Forwarded-For 时应用 X-Real-IP。"""
        request = self._make_request(headers={"X-Real-IP": "10.0.0.5"})
        assert _get_client_ip(request) == "10.0.0.5"

    def test_fallback_to_client_host(self):
        """无代理头时应回退到 request.client.host。"""
        request = self._make_request(client_host="192.168.1.100")
        assert _get_client_ip(request) == "192.168.1.100"

    def test_prefers_forwarded_over_real_ip(self):
        """X-Forwarded-For 优先级高于 X-Real-IP。"""
        request = self._make_request(
            headers={
                "X-Forwarded-For": "10.0.0.1",
                "X-Real-IP": "10.0.0.2",
            }
        )
        assert _get_client_ip(request) == "10.0.0.1"

    def test_forwarded_with_spaces(self):
        """X-Forwarded-For 中带空格的 IP 应被正确 trim。"""
        request = self._make_request(
            headers={"X-Forwarded-For": "  10.0.0.1  ,  192.168.1.1  "}
        )
        assert _get_client_ip(request) == "10.0.0.1"

    def test_no_ip_available_returns_empty(self):
        """没有任何 IP 信息时应返回空字符串。"""
        request = self._make_request()
        assert _get_client_ip(request) == ""


# =============================================================================
# RequestLogMiddleware 跳过路径测试
# =============================================================================


class TestSkipPaths:
    """请求日志跳过路径测试。"""

    def test_skip_paths_contains_docs_etc(self):
        """跳过路径列表应包含文档和静态资源路径。"""
        assert "/docs" in _SKIP_PATHS
        assert "/openapi.json" in _SKIP_PATHS
        assert "/redoc" in _SKIP_PATHS
        assert "/favicon.ico" in _SKIP_PATHS

    def test_skip_prefixes_contains_static_and_assets(self):
        """跳过前缀列表应包含 /static/ 和 /assets/。"""
        assert "/static/" in _SKIP_PREFIXES
        assert "/assets/" in _SKIP_PREFIXES


# =============================================================================
# LogAggregationService 测试
# =============================================================================


@pytest.mark.asyncio
class TestLogAggregationService:
    """LogAggregationService 定时任务测试。"""

    async def test_aggregate_job_handles_empty_data(self):
        """无数据时聚合任务应正常运行而不报错。"""
        service = LogAggregationService()

        with patch("backend.plugins.request_log.services._get_session_factory") as mock_get_sf:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_sf.return_value = MagicMock(return_value=mock_session)

            mock_result = MagicMock()
            mock_result.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)

            # 不应抛出异常
            await service._aggregate_job()

    async def test_cleanup_job_handles_empty_data(self):
        """无数据时清理任务应正常运行而不报错。"""
        service = LogAggregationService()

        with patch("backend.plugins.request_log.services._get_session_factory") as mock_get_sf:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)
            mock_get_sf.return_value = MagicMock(return_value=mock_session)

            mock_result = MagicMock()
            mock_result.scalar.return_value = 0
            mock_session.execute = AsyncMock(return_value=mock_result)

            # 不应抛出异常
            await service._cleanup_job()

    async def test_aggregate_job_logs_exception(self):
        """聚合任务异常应被捕获并记录日志，不向上抛出。"""
        service = LogAggregationService()

        with patch("backend.plugins.request_log.services._get_session_factory") as mock_get_sf:
            mock_get_sf.side_effect = RuntimeError("数据库连接失败")

            # 不应抛出异常
            await service._aggregate_job()

    async def test_cleanup_job_logs_exception(self):
        """清理任务异常应被捕获并记录日志，不向上抛出。"""
        service = LogAggregationService()

        with patch("backend.plugins.request_log.services._get_session_factory") as mock_get_sf:
            mock_get_sf.side_effect = RuntimeError("数据库连接失败")

            # 不应抛出异常
            await service._cleanup_job()

    async def test_start_does_not_raise_without_apscheduler(self):
        """APScheduler 未安装时 start 不应抛出异常。"""
        service = LogAggregationService()

        with patch.object(service, "_scheduler", None):
            # 模拟 import 失败
            import builtins

            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "apscheduler.schedulers.asyncio":
                    raise ImportError("No module named 'apscheduler'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                # 不应抛出异常
                service.start()

    async def test_start_is_idempotent(self):
        """多次调用 start 不应重复创建 scheduler。"""
        service = LogAggregationService()
        service.start()
        scheduler = service._scheduler
        service.start()
        # scheduler 引用应不变
        assert service._scheduler is scheduler

    async def test_stop_shuts_down_scheduler(self):
        """stop 应关闭 scheduler 并置为 None。"""
        service = LogAggregationService()
        service.start()

        if service._scheduler:
            service.stop()
            assert service._scheduler is None

    def test_stop_when_not_started(self):
        """未启动时调用 stop 不应抛出异常。"""
        service = LogAggregationService()
        service.stop()  # 不应抛出异常