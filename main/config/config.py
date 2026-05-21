"""
配置管理模块

从 .env 文件中读取配置。

使用方式：
    from config import Config

    # 使用显式定义的属性（推荐，简单直接）
    debug = Config.DEBUG

    # 使用 get 方法（适用于未显式定义的配置项）
    custom_value = Config.get("CUSTOM_KEY", "default")

添加新配置属性：
    在 _init_config_attributes() 函数中添加：
    Config.NEW_KEY = Config.get("NEW_KEY", "default_value")
"""

from pathlib import Path
from typing import Optional
from dotenv import dotenv_values


class Config:
    """配置类，从 .env 文件加载配置"""

    _config: dict[str, str] = {}
    _loaded: bool = False

    @classmethod
    def _load_config(cls) -> None:
        """从 .env 文件加载配置（仅加载一次）"""
        if cls._loaded:
            return

        # 获取项目根目录
        root_dir = Path(__file__).parent.parent

        # 从 .env 文件加载配置
        env_path = root_dir / ".env"
        if env_path.exists():
            env_config = dotenv_values(env_path)
            cls._config.update({k: v for k, v in env_config.items() if v is not None})
        else:
            print(f"Warning: .env file not found at {env_path}")

        cls._loaded = True

    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取配置值

        Args:
            key: 配置键名
            default: 默认值，如果配置不存在则返回此值

        Returns:
            配置值，如果不存在且未提供默认值则返回 None
        """
        cls._load_config()
        return cls._config.get(key, default)

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        """
        获取布尔类型配置值

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            布尔值
        """
        value = cls.get(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")

    @classmethod
    def get_int(cls, key: str, default: Optional[int] = None) -> Optional[int]:
        """
        获取整数类型配置值

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            整数值，如果转换失败则返回默认值
        """
        value = cls.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    @classmethod
    def get_float(cls, key: str, default: Optional[float] = None) -> Optional[float]:
        """
        获取浮点数类型配置值

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            浮点数值，如果转换失败则返回默认值
        """
        value = cls.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    @classmethod
    def __contains__(cls, key: str) -> bool:
        """支持 in 操作符"""
        cls._load_config()
        return key in cls._config


# 初始化配置属性
def _init_config_attributes() -> None:
    """初始化 Config 类的属性"""
    # 应用配置
    Config.APP_NAME = Config.get("APP_NAME", "llm_blanks_recog")
    Config.APP_VERSION = Config.get("APP_VERSION", "0.1.0")
    Config.APP_DESCRIPTION = Config.get("APP_DESCRIPTION", "AI 判题服务")

    # 服务器配置
    Config.DEBUG = Config.get_bool("DEBUG", False)

    # 日志配置
    Config.LOG_LEVEL = Config.get("LOG_LEVEL", "INFO")
    Config.LOG_PATH = Config.get(
        "LOG_PATH", f"/data/var/log/{Config.APP_NAME}/{Config.APP_NAME}.log"
    )
    Config.LOG_RETENTION_DAYS = Config.get_int("LOG_RETENTION_DAYS", 30)

    # API 配置
    Config.API_PREFIX = Config.get("API_PREFIX", "/api/v1")

    # 模型 API 配置（按区域分类）
    # 中国大陆模型统一配置
    Config.CN_API_KEY = Config.get("CN_API_KEY", "")
    Config.CN_BASE_URL = Config.get("CN_BASE_URL", "")
    # 中国大陆以外模型统一配置
    Config.GLOBAL_API_KEY = Config.get("GLOBAL_API_KEY", "")
    Config.GLOBAL_BASE_URL = Config.get("GLOBAL_BASE_URL", "")
    
    # Layout 检测 API 配置
    Config.LAYOUT_API_URL = Config.get("LAYOUT_API_URL", "https://cv.aixuexi.com/math_layout/predict")
    Config.LAYOUT_CHOICE_API_URL = Config.get("LAYOUT_CHOICE_API_URL", "https://cv.dev.aixuexi.com/layout/choice/predict")
    
    # OCR 识别 API 配置
    Config.LOCAL_PADDLE_OCR_URL = Config.get("LOCAL_PADDLE_OCR_URL", "https://cv.aixuexi.com/ocr/number/predict")
    Config.OCR_BLANKS_RECOG_URL = Config.get("OCR_BLANKS_RECOG_URL", "https://cv.aixuexi.com/formula_recog/")


# 初始化配置属性（模块导入时自动执行）
_init_config_attributes()
