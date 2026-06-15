"""中间件和错误处理测试。"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI

from backend.core.middleware import (
    AppError,
    AuthError,
    PermissionError,
    error_response,
    get_current_user,
    register_error_handlers,
    require_level,
    require_user,
    setup_cors,
)


class TestCustomExceptions:
    """测试自定义异常类。"""

    def test_app_error_base_class(self):
        """AppError 基类属性正确。"""
        exc = AppError(
            message="Test error",
            code="test_error",
            status_code=400,
            data={"key": "value"},
        )

        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.code == "test_error"
        assert exc.status_code == 400
        assert exc.data == {"key": "value"}

    def test_app_error_default_values(self):
        """AppError 默认值正确。"""
        exc = AppError("Test error")

        assert exc.code == "error"
        assert exc.status_code == 400
        assert exc.data == {}

    def test_auth_error(self):
        """AuthError 默认属性正确。"""
        exc = AuthError()

        assert exc.message == "未认证或认证已过期"
        assert exc.code == "auth_error"
        assert exc.status_code == 401

        # 自定义消息
        exc = AuthError("自定义认证错误")
        assert exc.message == "自定义认证错误"

    def test_permission_error(self):
        """PermissionError 默认属性正确。"""
        exc = PermissionError()

        assert exc.message == "权限不足"
        assert exc.code == "permission_denied"
        assert exc.status_code == 403

        # 自定义消息
        exc = PermissionError("自定义权限错误")
        assert exc.message == "自定义权限错误"


class TestErrorResponse:
    """测试错误响应工具函数。"""

    def test_error_response_format(self):
        """error_response 返回正确的JSON格式。"""
        response = error_response(
            message="Test error",
            code="test_code",
            status_code=400,
            data={"key": "value"},
        )

        assert response.status_code == 400
        assert response.media_type == "application/json"
        assert (
            response.body
            == b'{"code":"test_code","message":"Test error","data":{"key":"value"}}'
        )

    def test_error_response_default_values(self):
        """error_response 默认值正确。"""
        response = error_response("Test error")

        assert response.status_code == 400
        assert response.body == b'{"code":"error","message":"Test error","data":{}}'


class TestErrorHandlers:
    """测试错误处理函数。"""

    def test_error_handlers_registration(self):
        """测试错误处理器被正确注册到应用。"""
        app = FastAPI()
        register_error_handlers(app)

        # 验证异常处理器被注册
        assert AppError in app.exception_handlers
        assert Exception in app.exception_handlers


class TestCorsSetup:
    """测试CORS设置。"""

    def test_setup_cors(self):
        """setup_cors 正确添加CORS中间件。"""
        app = FastAPI()
        test_origins = ["http://localhost:5173", "https://example.com"]

        setup_cors(app, test_origins)

        # 检查中间件是否添加
        assert len(app.user_middleware) == 1
        middleware = app.user_middleware[0]
        from starlette.middleware.cors import CORSMiddleware

        assert middleware.cls is CORSMiddleware

        # 检查中间件选项（Middleware的kwargs是关键字参数字典）
        assert middleware.kwargs["allow_origins"] == test_origins
        assert middleware.kwargs["allow_credentials"] is True
        assert middleware.kwargs["allow_methods"] == ["*"]
        assert middleware.kwargs["allow_headers"] == ["*"]


class TestUserAuthUtils:
    """测试用户认证工具函数。"""

    def test_get_current_user_exists(self):
        """用户存在时 get_current_user 返回用户信息。"""
        mock_request = MagicMock()
        mock_request.state.user = {"id": 1, "name": "test", "level": 2}

        user = get_current_user(mock_request)
        assert user == {"id": 1, "name": "test", "level": 2}

    def test_get_current_user_not_exists(self):
        """用户不存在时 get_current_user 返回 None。"""
        mock_request = MagicMock()
        delattr(mock_request.state, "user")  # 确保没有user属性

        user = get_current_user(mock_request)
        assert user is None

    def test_require_user_exists(self):
        """用户存在时 require_user 返回用户信息。"""
        mock_request = MagicMock()
        mock_request.state.user = {"id": 1, "name": "test", "level": 2}

        user = require_user(mock_request)
        assert user == {"id": 1, "name": "test", "level": 2}

    def test_require_user_not_exists(self):
        """用户不存在时 require_user 抛出 AuthError。"""
        mock_request = MagicMock()
        delattr(mock_request.state, "user")

        with pytest.raises(AuthError, match="未认证或认证已过期"):
            require_user(mock_request)

    @pytest.mark.asyncio
    async def test_require_level_decorator_permitted(self):
        """用户等级满足要求时 require_level 装饰器正常放行。"""

        # 创建测试函数
        @require_level(min_level=3)
        async def test_func(request):
            return {"status": "ok"}

        # 用户等级2 <=3，应该放行
        mock_request = MagicMock()
        mock_request.state.user = {"id": 1, "level": 2}

        result = await test_func(request=mock_request)
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_require_level_decorator_denied(self):
        """用户等级不满足要求时抛出 PermissionError。"""

        @require_level(min_level=2)
        async def test_func(request):
            return {"status": "ok"}

        # 用户等级3 > 2，应该被拒绝
        mock_request = MagicMock()
        mock_request.state.user = {"id": 1, "level": 3}

        with pytest.raises(PermissionError, match="需要等级 <= 2，当前等级 3"):
            await test_func(request=mock_request)

    @pytest.mark.asyncio
    async def test_require_level_decorator_no_request_param(self):
        """路由没有request参数时抛出 AuthError。"""

        @require_level(min_level=2)
        async def test_func():  # 没有request参数
            return {"status": "ok"}

        with pytest.raises(AuthError, match="路由必须传入 request 参数"):
            await test_func()  # 不传request

    @pytest.mark.asyncio
    async def test_require_level_decorator_default_level(self):
        """用户没有level字段时默认等级5。"""

        @require_level(min_level=5)
        async def test_func(request):
            return {"status": "ok"}

        # 没有level字段，默认5，<=5，应该放行
        mock_request = MagicMock()
        mock_request.state.user = {"id": 1}

        result = await test_func(request=mock_request)
        assert result == {"status": "ok"}

        @require_level(min_level=4)
        async def test_func2(request):
            return {"status": "ok"}

        # 默认等级5 > 4，应该被拒绝
        with pytest.raises(PermissionError, match="需要等级 <= 4，当前等级 5"):
            await test_func2(request=mock_request)
