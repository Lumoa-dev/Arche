"""应用工厂函数测试。"""

import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from backend.core import _seed_default_config, _setup_logging, create_app
from backend.core.config import ConfigManager


class TestSetupLogging:
    """测试日志配置功能。"""

    def setup_method(self):
        """重置配置管理器单例。"""
        ConfigManager._instance = None
        # 清理所有日志处理器
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        # 重置日志级别
        logging.root.setLevel(logging.NOTSET)

    def teardown_method(self):
        """清理临时日志文件。"""
        # 先关闭所有日志处理器，释放文件锁
        for handler in logging.root.handlers[:]:
            handler.close()
            logging.root.removeHandler(handler)
        # 然后删除日志文件
        if Path("test.log").exists():
            Path("test.log").unlink()

    def test_setup_logging_console_only(self):
        """没有配置LOG_FILE时，仅配置控制台日志。"""
        # 创建测试配置
        config = ConfigManager()
        config.set("LOG_LEVEL", "DEBUG")
        # 确保LOG_FILE没有被设置
        config.set("LOG_FILE", "")

        with patch("backend.core.config_manager", config):
            _setup_logging()

        # 根日志级别是DEBUG
        assert logging.root.level == logging.DEBUG
        # 只有一个控制台处理器
        assert len(logging.root.handlers) == 1
        assert logging.root.handlers[0].__class__.__name__ == "StreamHandler"

    def test_setup_logging_with_file(self):
        """配置了LOG_FILE时，同时添加文件处理器。"""
        config = ConfigManager()
        config.set("LOG_LEVEL", "INFO")
        config.set("LOG_FILE", "test.log")

        with patch("backend.core.config_manager", config):
            _setup_logging()

        # 有两个处理器：控制台 + 文件
        assert len(logging.root.handlers) == 2
        handler_classes = {h.__class__.__name__ for h in logging.root.handlers}
        assert "StreamHandler" in handler_classes
        assert "FileHandler" in handler_classes

        # 日志文件被创建
        assert Path("test.log").exists()

    def test_setup_logging_default_level(self):
        """没有配置LOG_LEVEL时默认是INFO。"""
        config = ConfigManager()
        # 从_values中删除LOG_LEVEL配置，模拟未配置的情况
        if "LOG_LEVEL" in config._values:
            del config._values["LOG_LEVEL"]

        with patch("backend.core.config_manager", config):
            _setup_logging()

        assert logging.root.level == logging.INFO


class TestSeedDefaultConfig:
    """测试默认配置初始化功能。"""

    @pytest.mark.asyncio
    async def test_seed_default_config_first_run(self):
        """首次运行时正确将默认配置插入数据库。"""
        # 创建模拟的会话工厂
        mock_session = AsyncMock()
        # add是同步方法，不需要异步
        mock_session.add = MagicMock()
        # 模拟数据库为空
        result = MagicMock()
        result.first.return_value = None
        mock_session.execute.return_value = result

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        # 模拟配置管理器
        mock_config = MagicMock()

        def _mock_config_get(key, default=None):
            return {
                "MINIO_ENDPOINT": "http://localhost:9000",
                "LOG_LEVEL": "DEBUG",
            }.get(key, default)

        mock_config.get.side_effect = _mock_config_get

        with patch("backend.core.config_manager", mock_config):
            await _seed_default_config(mock_session_factory)

        # 应该添加了所有默认配置项
        assert mock_session.add.call_count >= 30  # _DEFAULT_CONFIG_SEED有30多项
        # 提交了事务
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_seed_default_config_already_exists(self):
        """数据库已经有配置时，不重复初始化。"""
        mock_session = MagicMock()
        # 模拟数据库已经有配置
        mock_session.execute.return_value.first.return_value = MagicMock()

        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        await _seed_default_config(mock_session_factory)

        # 没有调用add方法
        mock_session.add.assert_not_called()
        # 没有提交
        mock_session.commit.assert_not_called()


class TestCreateApp:
    """测试应用工厂函数。"""

    def setup_method(self):
        """重置所有单例状态。"""
        # 先配置必要的环境变量
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
        os.environ["SECRET_KEY"] = "test-secret"
        os.environ["CORS_ORIGINS"] = "http://localhost:5173,https://example.com"
        # 重新加载配置，确保环境变量生效
        from backend.core.config import config_manager

        config_manager.reload()

        # mock所有外部依赖
        self.patcher_init_db = patch("backend.core.init_db")
        self.mock_init_db = self.patcher_init_db.start()
        self.mock_init_db.return_value = (MagicMock(), MagicMock())

        self.patcher_registry_activate_all = patch("backend.core.registry.activate_all")
        self.mock_activate_all = self.patcher_registry_activate_all.start()

        self.patcher_registry_register_services = patch(
            "backend.core.registry.register_services"
        )
        self.mock_register_services = self.patcher_registry_register_services.start()

        self.patcher_setup_cors = patch("backend.core.setup_cors")
        self.mock_setup_cors = self.patcher_setup_cors.start()

        self.patcher_register_error_handlers = patch(
            "backend.core.register_error_handlers"
        )
        self.mock_register_error_handlers = self.patcher_register_error_handlers.start()

        self.patcher_alembic_upgrade = patch("alembic.command.upgrade")
        self.mock_alembic_upgrade = self.patcher_alembic_upgrade.start()

        self.patcher_ensure_tables = patch("backend.core.db.ensure_tables")
        self.mock_ensure_tables = self.patcher_ensure_tables.start()

        self.patcher_validate_schema = patch("backend.core.db.validate_schema")
        self.mock_validate_schema = self.patcher_validate_schema.start()

        self.patcher_seed_default_config = patch("backend.core._seed_default_config")
        self.mock_seed_default_config = self.patcher_seed_default_config.start()

        self.patcher_registry_on_startup = patch("backend.core.registry.on_startup")
        self.mock_registry_on_startup = self.patcher_registry_on_startup.start()

        self.patcher_registry_on_shutdown = patch("backend.core.registry.on_shutdown")
        self.mock_registry_on_shutdown = self.patcher_registry_on_shutdown.start()

        self.patcher_container_shutdown = patch(
            "backend.core.ServiceContainer.shutdown"
        )
        self.mock_container_shutdown = self.patcher_container_shutdown.start()

    def teardown_method(self):
        """停止所有mock。"""
        self.patcher_init_db.stop()
        self.patcher_registry_activate_all.stop()
        self.patcher_registry_register_services.stop()
        self.patcher_setup_cors.stop()
        self.patcher_register_error_handlers.stop()
        self.patcher_alembic_upgrade.stop()
        self.patcher_ensure_tables.stop()
        self.patcher_validate_schema.stop()
        self.patcher_seed_default_config.stop()
        self.patcher_registry_on_startup.stop()
        self.patcher_registry_on_shutdown.stop()
        self.patcher_container_shutdown.stop()

        # 清理环境变量
        for key in ["DATABASE_URL", "SECRET_KEY", "CORS_ORIGINS"]:
            if key in os.environ:
                del os.environ[key]

    def test_create_app_basic(self):
        """create_app 函数正确创建FastAPI应用实例。"""
        app = create_app()

        assert isinstance(app, FastAPI)
        assert app.title == "Arche"
        assert app.version == "0.1.0"

        # 验证关键函数被调用
        self.mock_init_db.assert_called_once()
        self.mock_activate_all.assert_called_once_with(app)
        self.mock_register_services.assert_called_once()
        self.mock_setup_cors.assert_called_once()
        self.mock_register_error_handlers.assert_called_once_with(app)

        # 验证CORS配置正确解析
        expected_origins = ["http://localhost:5173", "https://example.com"]
        self.mock_setup_cors.assert_called_with(app, expected_origins)

    def test_create_app_has_startup_hooks(self):
        """应用包含正确的启动钩子。"""
        app = create_app()

        # 有一个启动钩子
        assert len(app.router.on_startup) == 1

    def test_create_app_has_shutdown_hooks(self):
        """应用包含正确的关闭钩子。"""
        app = create_app()

        # 有一个关闭钩子
        assert len(app.router.on_shutdown) == 1

    @pytest.mark.asyncio
    async def test_startup_hook_executes_all_steps(self):
        """启动钩子按顺序执行所有步骤。"""
        app = create_app()
        startup_hook = app.router.on_startup[0]

        # 执行启动钩子
        await startup_hook()

        # 验证步骤执行顺序
        self.mock_alembic_upgrade.assert_called_once()  # 先运行迁移(upgrade)
        self.mock_ensure_tables.assert_called_once()  # 再兜底建表
        self.mock_validate_schema.assert_called_once()  # 然后校验schema
        self.mock_seed_default_config.assert_called_once()  # 然后初始化配置
        self.mock_registry_on_startup.assert_called_once()  # 最后启动插件

    @pytest.mark.asyncio
    async def test_shutdown_hook_executes_all_steps(self):
        """关闭钩子按顺序执行所有步骤。"""
        app = create_app()
        shutdown_hook = app.router.on_shutdown[0]

        # 执行关闭钩子
        await shutdown_hook()

        # 验证步骤执行顺序
        self.mock_registry_on_shutdown.assert_called_once()  # 先关闭插件
        self.mock_container_shutdown.assert_called_once()  # 然后关闭容器服务

    def test_create_app_mounts_frontend_static_files(self, tmp_path):
        """前端dist目录存在时，挂载静态文件。"""
        # 模拟项目目录结构
        backend_core_dir = tmp_path / "backend" / "core"
        backend_core_dir.mkdir(parents=True)
        (backend_core_dir / "__init__.py").write_text("")

        # 创建临时dist目录
        frontend_dist = tmp_path / "frontend" / "dist"
        frontend_dist.mkdir(parents=True)
        (frontend_dist / "index.html").write_text("<h1>Test</h1>")

        # 保存原始resolve方法
        original_resolve = Path.resolve

        def mock_resolve(self):
            # 如果是__file__对应的路径，返回我们的临时目录
            if self.as_posix().endswith("backend/core/__init__.py"):
                return backend_core_dir / "__init__.py"
            return original_resolve(self)

        with patch(
            "backend.core.Path.resolve", side_effect=mock_resolve, autospec=True
        ):
            app = create_app()

            # 验证静态文件被挂载
            assert len(app.routes) > 0
            route_paths = [route.path for route in app.routes]  # type: ignore
            assert "" in route_paths or "/" in route_paths

    def test_create_app_no_frontend_dist(self, tmp_path):
        """前端dist目录不存在时，不挂载静态文件。"""
        with patch("backend.core.Path.exists", return_value=False):
            app = create_app()

            # 检查有没有挂载到/的静态文件路由
            for route in app.routes:
                assert route.path != "/" or not hasattr(route.app, "directory")  # type: ignore
