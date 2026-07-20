"""请求日志服务测试 —— 行为分类、日志写入、聚合服务。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.plugins.request_log.services import (
    LogAggregationService,
    classify_action,
)


# =============================================================================
# 行为分类函数测试
# =============================================================================


class TestClassifyAction:
    """测试请求行为分类逻辑。"""

    def test_login_fail_returned_for_login_4xx(self):
        """登录接口的 4xx 返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 403) == "login_fail"
        assert classify_action("POST", "/api/auth/login", 429) == "login_fail"

    def test_login_success_not_login_fail(self):
        """登录成功不返回 login_fail。"""
        assert classify_action("POST", "/api/auth/login", 200) != "login_fail"

    def test_api_call_returned_for_api_paths(self):
        """API 路径返回 api_call。"""
        assert classify_action("GET", "/api/blog/posts", 200) == "api_call"
        assert classify_action("POST", "/api/admin/users", 201) == "api_call"

    def test_get_non_api_returns_page_view(self):
        """非 API 的 GET 请求返回 page_view。"""
        assert classify_action("GET", "/about", 200) == "page_view"
        assert classify_action("GET", "/", 200) == "page_view"

    def test_other_methods_return_other(self):
        """非 GET 且非 API 的请求返回 other。"""
        assert classify_action("POST", "/webhook/callback", 200) == "other"
        assert classify_action("PUT", "/some-resource", 200) == "other"

    def test_login_fail_takes_priority_over_api_call(self):
        """登录失败优先于 API 调用分类。"""
        assert classify_action("POST", "/api/auth/login", 401) == "login_fail"


# =============================================================================
# RequestLogMiddleware 测试
# =============================================================================


class TestSkipPaths:
    """测试跳过路径逻辑。"""

    def test_skip_docs_paths(self):
        """文档路径应被跳过。"""
        # 通过测试 _SKIP_PATHS 和 _SKIP_PREFIXES 的导入
        from backend.plugins.request_log.services import _SKIP_PATHS, _SKIP_PREFIXES

        assert "/docs" in _SKIP_PATHS
        assert "/openapi.json" in _SKIP_PATHS
        assert "/redoc" in _SKIP_PATHS
        assert "/static/" in _SKIP_PREFIXES
        assert "/assets/" in _SKIP_PREFIXES


# =============================================================================
# 日志写入辅助函数测试
# =============================================================================


class TestGetClientIp:
    """测试 IP 获取逻辑。"""

    def test_x_forwarded_for_takes_priority(self):
        """X-Forwarded-For 优先于 X-Real-IP。"""
        from backend.plugins.request_log.services import _get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {
            "X-Forwarded-For": "203.0.113.1, 10.0.0.1",
            "X-Real-IP": "192.168.1.1",
        }
        mock_request.client = MagicMock(host="127.0.0.1")

        result = _get_client_ip(mock_request)
        assert result == "203.0.113.1"

    def test_x_real_ip_fallback(self):
        """无 X-Forwarded-For 时用 X-Real-IP。"""
        from backend.plugins.request_log.services import _get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {"X-Real-IP": "192.168.1.1"}
        mock_request.client = MagicMock(host="127.0.0.1")

        result = _get_client_ip(mock_request)
        assert result == "192.168.1.1"

    def test_client_host_fallback(self):
        """无代理头时用 request.client.host。"""
        from backend.plugins.request_log.services import _get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = MagicMock(host="10.0.0.1")

        result = _get_client_ip(mock_request)
        assert result == "10.0.0.1"

    def test_empty_when_no_ip(self):
        """无任何 IP 来源时返回空字符串。"""
        from backend.plugins.request_log.services import _get_client_ip

        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None

        result = _get_client_ip(mock_request)
        assert result == ""


# =============================================================================
# LogAggregationService 测试
# =============================================================================


class TestLogAggregationService:
    """测试聚合服务生命周期。"""

    def test_start_stop_without_apscheduler(self, monkeypatch):
        """无 APScheduler 时 start 不抛异常。"""
        import builtins

        import backend.plugins.request_log.services as svc

        original_import = builtins.__import__

        def mock_import_func(name, *args, **kwargs):
            if "apscheduler" in name:
                raise ImportError
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import_func)
        with patch.object(svc.logger, "warning") as mock_warning:
            service = LogAggregationService()
            service.start()
            mock_warning.assert_called_once_with(
                "APScheduler 未安装，跳过定时任务启动"
            )

    async def test_aggregate_job_handles_exception(self):
        """聚合任务异常时记录日志不抛异常。"""
        from backend.plugins.request_log import services as svc

        service = LogAggregationService()
        with patch.object(svc.logger, "exception") as mock_exc:
            # _get_session_factory 返回 None 导致异常
            await service._aggregate_job()
            # 不应抛异常

    async def test_cleanup_job_handles_exception(self):
        """清理任务异常时记录日志不抛异常。"""
        from backend.plugins.request_log import services as svc

        service = LogAggregationService()
        with patch.object(svc.logger, "exception") as mock_exc:
            await service._cleanup_job()
            # 不应抛异常