"""
LLM 调用工具封装。

统一封装对兼容 OpenAI Chat Completions 接口的调用逻辑，避免在业务代码中散落
硬编码的 URL、API Key 和请求逻辑。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import requests
import httpx
from requests import RequestException, Timeout

from config.logger import logger
from config import Config


class XishuashuaAPIConfig:
    """喜刷刷API配置管理""" 

    def __init__(self,model_name: str):  
        self.url = ""
        self.api_key = ""
        self._load_from_apollo_if_needed(model_name)

    def _load_from_apollo_if_needed(self,resolved_provider_name: str):  
        """从Apollo加载配置（如果需要）"""
        if not self.url or not self.api_key:
            try:
                from .apollo import ApolloConfig
                ap_config = ApolloConfig(
                    config_server_url=Config.get("APOLLO_CONFIG_SERVER_URL", "http://apollo-pro-slb.ops.aixuexi.com:8083"),
                    cluster=Config.get("APOLLO_CLUSTER", "default"),
                    app_id=Config.get("APOLLO_APP_ID", "Password_Key"),
                    namespaces=[Config.get("APOLLO_NAMESPACE", "xishuashua_ocr")]
                )

                namespace = Config.get("APOLLO_NAMESPACE", "xishuashua_ocr")
                if resolved_provider_name == "aixuexi":
                    self.url = ap_config.get_str("AIXUEXI_CHAT_URL", namespace=namespace)
                    self.api_key = ap_config.get_str("AIXUEXI_CHAT_API_KEY", namespace=namespace)
                else:
                    self.url = ap_config.get_str("DASHSCOPE_CHAT_URL", namespace=namespace)
                    self.api_key = ap_config.get_str("DASHSCOPE_CHAT_API_KEY", namespace=namespace)
            except Exception as e:
                logger.warning(f"从Apollo获取配置失败: {e}")

    @property
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.api_key and self.url)



def _resolve_provider_by_model(model: str) -> str:
    """
    根据模型名称推断要使用的服务提供商。

    - 仅当 model == "gemini-3.0-flash-preview" 时走 AIXUEXI 代理（one-api）
    - 其他模型默认走 DashScope 兼容接口
    """
    normalized = model.strip()
    if normalized == "gemini-3.0-flash-preview":
        return "aixuexi"
    return "dashscope"


def chat_completions(
    messages: List[Dict[str, Any]],
    model: str,
    temperature: float = 0.0,
    timeout: float = 10.0,
    **kwargs: Any,
) -> Tuple[str, int]:
    """
    调用后端 Chat Completions 接口。

    相比原始实现做了以下改进：
    - URL 与 API Key 不再硬编码，统一从配置中读取；
    - 不再依赖未定义的常量（例如 GEMINI_3_FLASH），改为按 model 前缀推断；
    - 使用 requests 的 json 参数而不是手动 json.dumps；
    - 更合理的超时和错误处理，并记录日志。

    返回值：始终为 (response_text, status_code)。
    """
    resolved_provider = _resolve_provider_by_model(model)

    url = XishuashuaAPIConfig(resolved_provider).url
    api_key = XishuashuaAPIConfig(resolved_provider).api_key

    if not api_key:
        logger.error(
            "Chat Completions 调用失败：provider=%s 缺少 API Key 配置",
            resolved_provider,
        )
        return "Missing API key configuration", 500

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
        **kwargs,
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
    except Timeout:
        logger.warning(
            "Chat Completions 请求超时：provider=%s, model=%s, timeout=%s",
            resolved_provider,
            model,
            timeout,
        )
        return "Request timeout", 504
    except RequestException as exc:
        logger.error(
            "Chat Completions 请求异常：provider=%s, model=%s, error=%s",
            resolved_provider,
            model,
            exc,
        )
        return str(exc), 502
    except Exception as exc:  # 防御性捕获
        logger.exception(
            "Chat Completions 未预期异常：provider=%s, model=%s",
            resolved_provider,
            model,
        )
        return str(exc), 500

    # 与原始逻辑兼容：正常时固定返回 200，异常时返回真实状态码
    if response.status_code == 200:
        return response.text, 200
    return response.text, response.status_code


async def chat_completions_async(
    messages: List[Dict[str, Any]],
    model: str,
    temperature: float = 0.0,
    timeout: float = 60.0,
    **kwargs: Any,
) -> Tuple[str, int]:
    """
    异步调用后端 Chat Completions 接口。

    使用 httpx.AsyncClient 实现真正的异步 I/O，避免阻塞事件循环。

    返回值：始终为 (response_text, status_code)。
    """
    resolved_provider = _resolve_provider_by_model(model)

    url = XishuashuaAPIConfig(resolved_provider).url
    api_key = XishuashuaAPIConfig(resolved_provider).api_key

    if not api_key:
        logger.error(
            "Chat Completions 调用失败：provider=%s 缺少 API Key 配置",
            resolved_provider,
        )
        return "Missing API key configuration", 500

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
        **kwargs,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                headers=headers,
                json=payload,
            )
    except httpx.TimeoutException:
        logger.warning(
            "Chat Completions 请求超时：provider=%s, model=%s, timeout=%s",
            resolved_provider,
            model,
            timeout,
        )
        return "Request timeout", 504
    except httpx.RequestError as exc:
        logger.error(
            "Chat Completions 请求异常：provider=%s, model=%s, error=%s",
            resolved_provider,
            model,
            exc,
        )
        return str(exc), 502
    except Exception as exc:  # 防御性捕获
        logger.exception(
            "Chat Completions 未预期异常：provider=%s, model=%s",
            resolved_provider,
            model,
        )
        return str(exc), 500

    # 与原始逻辑兼容：正常时固定返回 200，异常时返回真实状态码
    if response.status_code == 200:
        return response.text, 200
    return response.text, response.status_code
