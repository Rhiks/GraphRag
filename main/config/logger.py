"""
日志管理模块

使用方式：
    from config.logger import logger
    logger.info("这是一条信息日志")
"""

import logging
import logging.config
from pathlib import Path

from config import Config


# 应用名称，用于日志器命名
APP_NAME = Config.APP_NAME


# 日志配置字典
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "[timestamp=%(asctime)s.%(msecs)03d] [app_id=%(name)s] [location=%(module)s.py:%(lineno)d] [method=%(funcName)s] [level=%(levelname)s] [msg=%(message)s]",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "%(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "detailed",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": "./log/server.log",
            "when": "midnight",
            "interval": 1,
            "backupCount": 30,
            "encoding": "utf-8",
            "utc": False,
        },
    },
    "loggers": {},
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}


def setup_logger() -> logging.Logger:
    """设置并返回配置好的日志器"""
    # 从 Config 动态设置日志路径和级别
    config = LOGGING_CONFIG.copy()

    # 动态设置 logger 配置
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    config["loggers"][APP_NAME] = {
        "level": log_level,
        "handlers": ["console", "file"],
        "propagate": False,
    }

    # 设置日志文件路径
    if Config.LOG_PATH:
        log_path = Path(Config.LOG_PATH)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        config["handlers"]["file"]["filename"] = str(log_path)

    # 设置日志保留天数
    if Config.LOG_RETENTION_DAYS:
        config["handlers"]["file"]["backupCount"] = Config.LOG_RETENTION_DAYS

    # 设置处理器日志级别
    config["handlers"]["console"]["level"] = log_level
    config["handlers"]["file"]["level"] = log_level

    logging.config.dictConfig(config)
    return logging.getLogger(APP_NAME)


# 创建全局日志器实例
logger = setup_logger()
