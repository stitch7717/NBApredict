"""
日志配置
"""
import sys
from loguru import logger
from config.settings import LOG_DIR

def setup_logger():
    """配置日志"""
    # 移除默认handler
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
    )

    # 文件输出 - 按日期分割
    logger.add(
        LOG_DIR / "algorithm_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
    )

    # 错误日志单独存储
    logger.add(
        LOG_DIR / "error_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
    )

    return logger
