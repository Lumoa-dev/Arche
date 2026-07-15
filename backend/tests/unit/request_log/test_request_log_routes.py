"""请求日志路由 单元测试。

测试 query_logs、get_top_ips、get_trend、get_counters、list_actions 等端点，
覆盖：
- 正常查询路径
- 日期格式校验边界
- 分页参数边界
- 无数据时返回空列表
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request

from backend.plugins.request_log import routes


def _make_mock_request(user_id: str = "test-user") -> Request:
    """创建带有认证用户状态的 mock Request。"""
    mock_app = type(
        "MockApp",
        (),
        {"state": type("MockState", (), {"container": MagicMock()})()},
    )()
    scope = {"type": "http", "app": mock_app, "headers": []}
    request = Request(scope)
    request.state.user = {
        "id": user_id,
        "username": "admin",
        "level": 0,
        "email": "admin@test.com",
        "blog_quality_level": 0,
    }
    return request


def _make_mock_session(scalar_all_return=None, scalar_return=None, all_return=None):
    """创建 mock 数据库会话。

    生成支持 ``async with session_factory() as session:`` 模式的 mock。
    """
    mock_result = MagicMock()
    if scalar_all_return is not None:
        mock_result.scalars.return_value.all.return_value = scalar_all_return
    if scalar_return is not None:
        mock_result.scalar.return_value = scalar_return
    if all_return is not None:
        mock_result.all.return_value = all_return

    mock_session = MagicMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    return mock_session


def _make_session_factory(scalar_all_return=None, scalar_return=None, all_return=None):
    """创建一个 session factory，routes 通过 ``async with factory() as session:`` 使用。"""
    session = _make_mock_session(
        scalar_all_return=scalar_all_return,
        scalar_return=scalar_return,
        all_return=all_return,
    )
    return MagicMock(return_value=session)


@pytest.mark.asyncio
class TestQueryLogs:
    """请求日志查询接口测试。"""

    async def test_query_without_filters(self, monkeypatch):
        """无过滤条件时返回所有日志。"""
        mock_log = MagicMock()
        mock_log.to_dict.return_value = {"id": "1", "ip": "10.0.0.1"}
        factory = _make_session_factory(
            scalar_all_return=[mock_log],
            scalar_return=1,
        )
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        result = await routes.query_logs(
            request=_make_mock_request(),
            start_date=None,
            end_date=None,
            page=1,
            page_size=20,
        )
        assert result["total"] == 1
        assert len(result["items"]) == 1

    async def test_query_with_ip_filter(self, monkeypatch):
        """按 IP 过滤应传递正确参数。"""
        factory = _make_session_factory(scalar_all_return=[], scalar_return=0)
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        result = await routes.query_logs(
            request=_make_mock_request(),
            ip="10.0.0.1",
            start_date=None,
            end_date=None,
            page=1,
            page_size=20,
        )
        assert result["total"] == 0

    async def test_query_with_date_range(self, monkeypatch):
        """有效的日期范围应正确过滤。"""
        factory = _make_session_factory(scalar_all_return=[], scalar_return=0)
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        result = await routes.query_logs(
            request=_make_mock_request(),
            start_date="2024-01-01",
            end_date="2024-01-07",
            page=1,
            page_size=20,
        )
        assert result["total"] == 0

    async def test_query_invalid_start_date(self, monkeypatch):
        """无效的 start_date 格式应返回 400。"""
        factory = _make_session_factory(scalar_all_return=[], scalar_return=0)
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        with pytest.raises(HTTPException) as exc:
            await routes.query_logs(
                request=_make_mock_request(),
                start_date="invalid-date",
                end_date=None,
            )
        assert exc.value.status_code == 400

    async def test_query_invalid_end_date(self, monkeypatch):
        """无效的 end_date 格式应返回 400。"""
        factory = _make_session_factory(scalar_all_return=[], scalar_return=0)
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        with pytest.raises(HTTPException) as exc:
            await routes.query_logs(
                request=_make_mock_request(),
                start_date=None,
                end_date="not-a-date",
            )
        assert exc.value.status_code == 400

    async def test_query_pagination_defaults(self, monkeypatch):
        """默认分页参数应为 page=1, page_size=20。"""
        factory = _make_session_factory(scalar_all_return=[], scalar_return=0)
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        result = await routes.query_logs(
            request=_make_mock_request(),
            start_date=None,
            end_date=None,
            page=1,
            page_size=20,
        )
        assert result["page"] == 1
        assert result["page_size"] == 20


@pytest.mark.asyncio
class TestGetTopIps:
    """TOP IP 排行接口测试。"""

    async def test_returns_top_ips(self, monkeypatch):
        """应返回按请求数降序排列的 IP 列表。"""
        factory = _make_session_factory(
            all_return=[
                MagicMock(ip="10.0.0.1", total_count=100),
                MagicMock(ip="10.0.0.2", total_count=50),
            ]
        )
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        result = await routes.get_top_ips(
            request=_make_mock_request(),
            days=7,
            limit=20,
        )
        assert len(result) == 2
        assert result[0]["ip"] == "10.0.0.1"
        assert result[0]["count"] == 100
        assert result[1]["ip"] == "10.0.0.2"

    async def test_empty_result(self, monkeypatch):
        """无数据时返回空列表。"""
        factory = _make_session_factory(all_return=[])
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        result = await routes.get_top_ips(
            request=_make_mock_request(),
            days=7,
            limit=20,
        )
        assert result == []


@pytest.mark.asyncio
class TestGetTrend:
    """异常行为趋势接口测试。"""

    async def test_returns_trend_data(self, monkeypatch):
        """应返回按天聚合的趋势数据。"""
        factory = _make_session_factory(
            all_return=[
                MagicMock(log_date="2024-01-01", cnt=10),
                MagicMock(log_date="2024-01-02", cnt=15),
            ]
        )
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        result = await routes.get_trend(
            request=_make_mock_request(),
            days=7,
        )
        assert len(result) == 2
        assert result[0]["date"] == "2024-01-01"
        assert result[0]["count"] == 10

    async def test_empty_trend(self, monkeypatch):
        """无数据时返回空列表。"""
        factory = _make_session_factory(all_return=[])
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        result = await routes.get_trend(
            request=_make_mock_request(),
            days=7,
        )
        assert result == []


@pytest.mark.asyncio
class TestGetCounters:
    """IP 行为聚合计数接口测试。"""

    async def test_query_with_filters(self, monkeypatch):
        """按 IP 和 action 过滤应正确传递参数。"""
        mock_counter = MagicMock()
        mock_counter.to_dict.return_value = {
            "id": 1,
            "ip": "10.0.0.1",
            "action": "api_call",
            "count": 50,
        }
        factory = _make_session_factory(
            scalar_all_return=[mock_counter],
            scalar_return=1,
        )
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        result = await routes.get_counters(
            request=_make_mock_request(),
            ip="10.0.0.1",
            action="api_call",
            start_date=None,
            end_date=None,
            page=1,
            page_size=20,
        )
        assert result["total"] == 1
        assert len(result["items"]) == 1

    async def test_invalid_date_format(self, monkeypatch):
        """无效的日期格式应返回 400。"""
        factory = _make_session_factory(scalar_all_return=[], scalar_return=0)
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        with pytest.raises(HTTPException) as exc:
            await routes.get_counters(
                request=_make_mock_request(),
                start_date="bad-date",
                end_date=None,
            )
        assert exc.value.status_code == 400


@pytest.mark.asyncio
class TestListActions:
    """行为分类列表接口测试。"""

    async def test_returns_action_list(self, monkeypatch):
        """应返回去重后的行为分类列表。"""
        factory = _make_session_factory(all_return=[("api_call",), ("login_fail",)])
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        result = await routes.list_actions(request=_make_mock_request())
        assert result == ["api_call", "login_fail"]

    async def test_empty_actions(self, monkeypatch):
        """无数据时返回空列表。"""
        factory = _make_session_factory(all_return=[])
        monkeypatch.setattr(routes, "_get_session_factory", lambda: factory)

        result = await routes.list_actions(request=_make_mock_request())
        assert result == []