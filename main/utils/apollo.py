"""
Apollo 配置中心客户端封装

用于与携程 Apollo 配置中心交互的 Python 客户端。
"""

import logging
import threading
import time
import json
import os
import ast
import requests
from typing import Any, Optional, Dict

try:
    from apollo_client import ApolloClient
except ImportError:
    ApolloClient = None


class ApolloConfig:
    """
    Apollo 配置中心客户端封装类
    
    功能：
    - 初始化 Apollo 客户端连接
    - 配置值的获取与类型转换
    - 配置变更监听与自动更新
    - 本地缓存管理
    - 后台定时刷新
    
    使用示例：
        >>> config = ApolloConfig(
        ...     config_server_url="http://apollo.config.server:8000",
        ...     app_id="your-app-id",
        ...     cluster="default"
        ... )
        >>> db_url = config.get("database.url")
    """
    
    def __init__(
        self,
        config_server_url: str = "http://apollo-pro-slb.ops.aixuexi.com:8083",
        app_id: str = "studentAttentionAnalysis",
        cluster: str = "default",
        namespaces: list = None,
        default_cache_path: Optional[str] = None, 
        file_path: Optional[str] = None, 
    ):
        """
        初始化 Apollo 配置客户端
        
        Args:
            config_server_url: Apollo 配置服务器地址
            app_id: 应用 ID
            cluster: 集群名称，默认为 "default"
            namespaces: 要监听的命名空间列表
            default_cache_path: 默认缓存文件路径
            file_path: Apollo 客户端缓存文件路径
        """
        self.logger = logging.getLogger(__name__)
        self.config_server_url = config_server_url
        self.app_id = app_id
        self.cluster = cluster
        self.namespaces = namespaces or ["application"]
        self.default_cache_path = default_cache_path
        self._file_path = file_path
        
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        self._stop_event = threading.Event()
        self.default_config_cache = {}
        self.client = None
        
        # 如果 pyapollo 可用，初始化 Apollo 客户端
        if ApolloClient:
            try:
                self.client = ApolloClient(
                    config_server_url=config_server_url,
                    app_id=app_id,
                    cluster=cluster,
                    cache_file_path=file_path,
                )
                self.client.start()
                time.sleep(2)  # 等待客户端初始化
                
                # 初始加载配置
                self._load_default_configs()
                self._load_cache_configs()
                
                # 主动触发加载所有命名空间的配置
                for namespace in self.namespaces:
                    if namespace != "application":
                        try:
                            if hasattr(self.client, 'get_value'):
                                self.client.get_value("__init_load__", default_val=None, namespace=namespace)
                                time.sleep(0.5)
                        except Exception as e:
                            self.logger.debug(f"触发命名空间 {namespace} 加载时出错: {e}")
            except Exception as e:
                self.logger.warning(f"Apollo 客户端初始化失败: {e}")
    
    def _load_default_configs(self) -> None:
        """加载默认配置缓存"""
        result = {}
        if self.default_cache_path and os.path.isfile(self.default_cache_path):
            try:
                with open(self.default_cache_path, 'r') as f:
                    result = json.loads(f.readline())
            except Exception as e:
                self.logger.debug(f"加载默认缓存失败: {e}")
        
        if result and "configurations" in result:
            self.default_config_cache = {"application": result["configurations"]}
        else:
            self.default_config_cache = {}
    
    def _get_config_via_http(self, namespace: str) -> Dict[str, Any]:
        """
        直接使用 HTTP API 获取 Apollo 配置
        
        Args:
            namespace: 命名空间名称
            
        Returns:
            配置字典
        """
        try:
            url = f"{self.config_server_url}/configs/{self.app_id}/{self.cluster}/{namespace}"
            self.logger.debug(f"尝试通过 HTTP API 获取配置: {url}")
            
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                config_data = response.json()
                self.logger.debug(f"HTTP API 返回配置: {config_data}")
                if "configurations" in config_data:
                    return config_data["configurations"]
                elif isinstance(config_data, dict):
                    return config_data
            else:
                self.logger.warning(f"HTTP API 请求失败，状态码: {response.status_code}")
        except Exception as e:
            self.logger.debug(f"通过 HTTP API 获取配置失败: {e}")
        return {}
    
    def _load_cache_configs(self) -> None:
        """加载所有命名空间配置到本地缓存"""
        for namespace in self.namespaces:
            try:
                namespace_config = {}
                
                # 方法1: 尝试从 Apollo 客户端的 _cache 获取配置
                if self.client and hasattr(self.client, '_cache') and self.client._cache:
                    if isinstance(self.client._cache, dict):
                        if namespace in self.client._cache:
                            namespace_config = self.client._cache[namespace]
                        else:
                            for key, value in self.client._cache.items():
                                if isinstance(value, dict) and namespace in str(key):
                                    namespace_config = value
                                    break
                
                # 方法2: 如果缓存中没有找到，尝试主动触发加载命名空间
                if not namespace_config and self.client and hasattr(self.client, 'get_value'):
                    try:
                        self.client.get_value("__dummy_key__", default_val=None, namespace=namespace)
                        time.sleep(0.5)
                        if hasattr(self.client, '_cache') and self.client._cache:
                            if isinstance(self.client._cache, dict) and namespace in self.client._cache:
                                namespace_config = self.client._cache[namespace]
                    except Exception as e:
                        self.logger.debug(f"触发加载命名空间 {namespace} 失败: {e}")
                
                # 方法3: 如果 pyapollo 无法加载，尝试使用 HTTP API 直接获取
                if not namespace_config and namespace != "application":
                    http_configs = self._get_config_via_http(namespace)
                    if http_configs:
                        namespace_config = http_configs
                        if self.client and hasattr(self.client, '_cache') and self.client._cache:
                            if namespace not in self.client._cache:
                                self.client._cache[namespace] = {}
                            self.client._cache[namespace].update(http_configs)
                
                if not namespace_config:
                    namespace_config = {}
                
                self._config_cache[namespace] = namespace_config
                self.logger.debug(f"成功加载命名空间 {namespace} 的配置，共 {len(namespace_config)} 个配置项")
            except Exception as e:
                self.logger.error(f"加载命名空间 {namespace} 配置失败: {e}")
                self._config_cache[namespace] = self.default_config_cache.get(namespace, {})
    
    def get(self, key: str, default: Any = None, namespace: str = "application") -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            namespace: 命名空间
            
        Returns:
            配置值
        """
        try:
            # 优先使用 HTTP API 直接获取最新配置
            if namespace != "application":
                http_configs = self._get_config_via_http(namespace)
                if http_configs and key in http_configs:
                    return http_configs[key]
            
            # 如果 HTTP API 失败，尝试使用 pyapollo 的 get_value 方法
            if self.client and hasattr(self.client, 'get_value'):
                try:
                    value = self.client.get_value(key, default_val=default, namespace=namespace)
                    if value is not None and value != "":
                        return value
                except Exception as e:
                    self.logger.debug(f"使用 get_value 方法获取配置 {key} 失败: {e}")
            
            # 最后尝试从 _cache 中获取
            if self.client and hasattr(self.client, '_cache') and self.client._cache:
                if isinstance(self.client._cache, dict):
                    if namespace in self.client._cache:
                        namespace_data = self.client._cache[namespace]
                        if isinstance(namespace_data, dict) and key in namespace_data:
                            value = namespace_data[key]
                            if value is not None:
                                return value
        except Exception as e:
            self.logger.debug(f"从 Apollo 客户端获取配置 {key} 失败: {e}")
        
        return default
    
    def get_str(self, key: str, default: str = "", namespace: str = "application") -> str:
        """获取字符串类型配置"""
        value = self.get(key, default, namespace)
        return str(value) if value is not None else default
    
    def get_int(self, key: str, default: int = 0, namespace: str = "application") -> int:
        """获取整数类型配置"""
        try:
            value = self.get(key, default, namespace)
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            self.logger.warning(f"配置 {key} 不是有效的整数，使用默认值 {default}")
            return default
    
    def get_float(self, key: str, default: float = 0.0, namespace: str = "application") -> float:
        """获取浮点数类型配置"""
        try:
            value = self.get(key, default, namespace)
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            self.logger.warning(f"配置 {key} 不是有效的浮点数，使用默认值 {default}")
            return default
    
    def get_bool(self, key: str, default: bool = False, namespace: str = "application") -> bool:
        """获取布尔类型配置"""
        value = self.get(key, default, namespace)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "y", "t")
        return bool(value)
    
    def get_dict(self, key: str, default: dict = None, namespace: str = "application") -> dict:
        """获取字典类型配置(JSON格式)"""
        value = self.get(key, default, namespace)
        if value is None:
            return default or {}
        try:
            return json.loads(value) if isinstance(value, str) else value
        except json.JSONDecodeError:
            self.logger.warning(f"配置 {key} 不是有效的JSON，使用默认值")
            return default or {}
    
    def get_list(self, key: str, default: list = None, namespace: str = "application") -> list:
        """获取列表类型配置"""
        value = self.get(key, default, namespace)
        if value is None:
            return default or []
        try:
            if isinstance(value, str):
                return ast.literal_eval(value.replace("\n", '').replace(" ", ''))
            return list(value)
        except (ValueError, SyntaxError):
            self.logger.warning(f"配置 {key} 不是有效的列表，使用默认值")
            return default or []
    
    def stop(self) -> None:
        """停止自动刷新"""
        self._stop_event.set()
        if self.client and hasattr(self, "thread") and self.thread.is_alive():
            self.thread.join()
        if self.client:
            self.client.stop()
        self.logger.info("Apollo 配置客户端已停止")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
