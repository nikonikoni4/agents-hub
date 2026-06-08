"""
Logger 模块测试
"""

import logging

import pytest

from agents_hub.utils.logger import (
    RotatingFileHandler,
    TruncatingFormatter,
    get_logger,
    get_specialized_logger,
    setup_logging,
)


@pytest.fixture
def temp_log_dir(tmp_path):
    """临时日志目录"""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture(autouse=True)
def reset_logging():
    """每个测试前重置 logging 状态"""
    # 清理所有 handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)

    # 清理所有已创建的 logger
    for name in list(logging.Logger.manager.loggerDict.keys()):
        if name.startswith("special") or name.startswith("agent") or name.startswith("private"):
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

    # 重置模块级状态
    import agents_hub.utils.logger as logger_module
    logger_module._initialized = False
    logger_module._global_log_dir = None

    yield

    # 测试后清理
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)


class TestTruncatingFormatter:
    """测试日志截断格式化器"""

    def test_short_message_not_truncated(self):
        """短消息不应被截断"""
        formatter = TruncatingFormatter(max_length=100)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="短消息",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "短消息" in result
        assert "截断" not in result

    def test_long_message_truncated(self):
        """超长消息应被截断"""
        formatter = TruncatingFormatter(max_length=50)
        long_msg = "x" * 200
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=long_msg,
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert len(result) < len(long_msg) + 100  # 截断后应该更短
        assert "截断" in result
        assert "原长 " in result


class TestRotatingFileHandler:
    """测试日志轮转处理器"""

    def test_no_rotation_for_small_file(self, temp_log_dir):
        """小文件不应触发轮转"""
        log_file = temp_log_dir / "test.log"
        handler = RotatingFileHandler(log_file, max_bytes=1000)

        # 写入少量数据
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="小消息",
            args=(),
            exc_info=None,
        )
        handler.emit(record)
        handler.close()

        # 不应生成 .old.log
        old_log = temp_log_dir / "test.old.log"
        assert not old_log.exists()

    def test_rotation_when_exceeds_max_bytes(self, temp_log_dir):
        """超过阈值应触发轮转"""
        log_file = temp_log_dir / "test.log"
        handler = RotatingFileHandler(log_file, max_bytes=500)
        handler.setFormatter(logging.Formatter("%(message)s"))

        # 写入大量数据
        for i in range(100):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="x" * 50,
                args=(),
                exc_info=None,
            )
            handler.emit(record)

        handler.close()

        # 应生成 .old.log
        old_log = temp_log_dir / "test.old.log"
        assert old_log.exists()
        assert old_log.stat().st_size > 500

    def test_old_log_overwritten_on_second_rotation(self, temp_log_dir):
        """第二次轮转应覆盖旧的 .old.log"""
        log_file = temp_log_dir / "test.log"
        old_log = temp_log_dir / "test.old.log"

        # 第一次轮转
        handler = RotatingFileHandler(log_file, max_bytes=100)
        handler.setFormatter(logging.Formatter("%(message)s"))
        for _ in range(50):
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="test.py",
                lineno=1, msg="x" * 10, args=(), exc_info=None,
            )
            handler.emit(record)
        handler.close()

        first_old_size = old_log.stat().st_size

        # 第二次轮转
        handler = RotatingFileHandler(log_file, max_bytes=100)
        handler.setFormatter(logging.Formatter("%(message)s"))
        for _ in range(50):
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="test.py",
                lineno=1, msg="y" * 10, args=(), exc_info=None,
            )
            handler.emit(record)
        handler.close()

        # .old.log 应被覆盖
        assert old_log.exists()
        # 内容应该是 'y' 而不是 'x'
        content = old_log.read_text(encoding="utf-8")
        assert "y" in content


class TestSetupLogging:
    """测试日志系统初始化"""

    def test_setup_creates_log_directory(self, temp_log_dir):
        """初始化应创建日志目录"""
        new_dir = temp_log_dir / "new_logs"
        setup_logging(new_dir)
        assert new_dir.exists()

    def test_setup_creates_global_log_file(self, temp_log_dir):
        """初始化应创建全局日志文件"""
        setup_logging(temp_log_dir, global_log_filename="test.log")
        log_file = temp_log_dir / "test.log"

        # 写入日志
        logger = logging.getLogger("test")
        logger.info("测试消息")

        # 应写入文件
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "测试消息" in content

    def test_setup_only_once(self, temp_log_dir):
        """重复调用 setup_logging 应被忽略"""
        setup_logging(temp_log_dir, global_log_filename="first.log")
        setup_logging(temp_log_dir, global_log_filename="second.log")

        # 只应创建第一个文件
        assert (temp_log_dir / "first.log").exists()


class TestGetLogger:
    """测试获取标准 logger"""

    def test_get_logger_returns_logger(self):
        """应返回 logger 实例"""
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test"

    def test_get_logger_with_level(self):
        """应设置指定的日志级别"""
        logger = get_logger("test", level=logging.DEBUG)
        assert logger.level == logging.DEBUG


class TestGetSpecializedLogger:
    """测试获取特定用途的 logger"""

    def test_requires_setup_first(self):
        """未初始化时应抛出异常"""
        with pytest.raises(RuntimeError, match="必须先调用 setup_logging"):
            get_specialized_logger("test", "test.log")

    def test_creates_specialized_log_file(self, temp_log_dir):
        """应创建专用日志文件"""
        setup_logging(temp_log_dir)
        logger = get_specialized_logger("special", "special.log")
        logger.info("专用消息")

        special_file = temp_log_dir / "special.log"
        assert special_file.exists()
        content = special_file.read_text(encoding="utf-8")
        assert "专用消息" in content

    def test_also_to_global_true(self, temp_log_dir):
        """also_to_global=True 时应同时写入全局日志"""
        setup_logging(temp_log_dir, global_log_filename="global.log")
        logger = get_specialized_logger("special", "special.log", also_to_global=True)
        logger.info("测试消息")

        # 强制 flush 所有 handlers
        for handler in logger.handlers:
            handler.flush()
        for handler in logging.getLogger().handlers:
            handler.flush()

        # 应同时写入两个文件
        special_file = temp_log_dir / "special.log"
        global_file = temp_log_dir / "global.log"

        assert special_file.exists()
        assert global_file.exists()

        special_content = special_file.read_text(encoding="utf-8")
        global_content = global_file.read_text(encoding="utf-8")

        assert "测试消息" in special_content
        assert "测试消息" in global_content

    def test_also_to_global_false(self, temp_log_dir):
        """also_to_global=False 时不应写入全局日志"""
        setup_logging(temp_log_dir, global_log_filename="global.log")
        logger = get_specialized_logger("special", "special.log", also_to_global=False)
        logger.info("专用消息")

        # 强制 flush 所有 handlers
        for handler in logger.handlers:
            handler.flush()
        for handler in logging.getLogger().handlers:
            handler.flush()

        special_file = temp_log_dir / "special.log"
        global_file = temp_log_dir / "global.log"

        special_content = special_file.read_text(encoding="utf-8")
        global_content = global_file.read_text(encoding="utf-8")

        # 只应在专用文件中
        assert "专用消息" in special_content
        assert "专用消息" not in global_content

    def test_prevents_duplicate_handlers(self, temp_log_dir):
        """重复获取同一 logger 不应添加重复的 handler"""
        setup_logging(temp_log_dir)
        logger1 = get_specialized_logger("special", "special.log")
        logger2 = get_specialized_logger("special", "special.log")

        assert logger1 is logger2
        # 应该只有一个 FileHandler
        file_handlers = [h for h in logger1.handlers if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 1

    def test_custom_log_dir(self, temp_log_dir):
        """应支持自定义日志目录"""
        setup_logging(temp_log_dir)
        custom_dir = temp_log_dir / "custom" / "path"

        logger = get_specialized_logger(
            name="custom_logger",
            log_filename="custom.log",
            log_dir=custom_dir
        )
        logger.info("自定义路径消息")

        # 强制 flush
        for handler in logger.handlers:
            handler.flush()

        # 应在自定义目录中创建文件
        custom_file = custom_dir / "custom.log"
        assert custom_file.exists()
        content = custom_file.read_text(encoding="utf-8")
        assert "自定义路径消息" in content

        # 不应在全局目录创建
        global_file = temp_log_dir / "custom.log"
        assert not global_file.exists()


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self, temp_log_dir):
        """测试完整的日志工作流"""
        # 1. 初始化
        setup_logging(temp_log_dir, global_log_filename="app.log")

        # 2. 使用全局 logger
        global_logger = get_logger("main")
        global_logger.info("应用启动")

        # 3. 使用 specialized logger
        agent_logger = get_specialized_logger("agent", "agent.log", also_to_global=True)
        agent_logger.info("Agent 消息")

        # 4. 验证文件
        app_log = temp_log_dir / "app.log"
        agent_log = temp_log_dir / "agent.log"

        assert app_log.exists()
        assert agent_log.exists()

        app_content = app_log.read_text(encoding="utf-8")
        agent_content = agent_log.read_text(encoding="utf-8")

        # 全局日志应包含两条消息
        assert "应用启动" in app_content
        assert "Agent 消息" in app_content

        # 专用日志只包含 Agent 消息
        assert "应用启动" not in agent_content
        assert "Agent 消息" in agent_content

    def test_log_rotation_integration(self, temp_log_dir):
        """测试日志轮转集成"""
        setup_logging(temp_log_dir, global_log_filename="rotation.log")
        logger = get_logger("test")

        # 写入大量日志触发轮转
        for i in range(1000):
            logger.info("x" * 500)

        log_file = temp_log_dir / "rotation.log"
        old_log = temp_log_dir / "rotation.old.log"

        # 应触发轮转
        assert old_log.exists()
        assert old_log.stat().st_size > 500 * 1024  # 超过 500KB
