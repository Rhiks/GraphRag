"""
聊天服务工厂和统一接口
"""

import asyncio
from typing import Optional, AsyncIterator, Any

from config import Config
from config.logger import logger
from constants.model_names import QWEN3_VL_PLUS
from model.chat import ChatMessage
from .openai_service import OpenAIService


# 模型配置
# 所有模型都通过 one_api 统一接口访问，使用 OpenAI 格式
_MODEL_CONFIGS: dict[str, dict[str, Any]] = {
    "qwen3-vl-plus": {
        "is_cn_region": True,
    },
    QWEN3_VL_PLUS: {
        "is_cn_region": True,
    },
    "gpt-4.1": {
        "is_cn_region": False,
    },
    "gpt-5-chat-latest": {
        "is_cn_region": False,
    },
    "gemini-3-flash-preview": {
        "is_cn_region": False,
    },
}


class ChatService:
    """聊天服务统一接口"""

    @staticmethod
    def create_model_service(model_name: str) -> OpenAIService:
        """
        根据模型名称创建对应的服务实例

        Args:
            model_name: 模型名称

        Returns:
            OpenAIService: 模型服务实例

        Raises:
            ValueError: 如果模型名称不支持
        """

        if model_name not in _MODEL_CONFIGS:
            raise ValueError(
                f"Unsupported model: {model_name}. Supported models: {list(_MODEL_CONFIGS.keys())}"
            )

        # 根据模型区域获取对应的 API 密钥和配置
        is_cn_region = _MODEL_CONFIGS[model_name]["is_cn_region"]

        if is_cn_region:
            # 使用中国大陆的统一配置
            base_url = Config.CN_BASE_URL
            api_key = Config.CN_API_KEY
        else:
            # 使用中国大陆以外的统一配置
            base_url = Config.GLOBAL_BASE_URL
            api_key = Config.GLOBAL_API_KEY

        # 所有模型都使用 OpenAIService，通过 one_api 统一接口访问
        # 仅模型名称和配置（base_url, api_key）不同
        return OpenAIService(model_name=model_name, base_url=base_url, api_key=api_key)

    @staticmethod
    async def stream_completions(
        model: str,
        messages: list[ChatMessage],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        流式生成聊天完成响应

        Args:
            model: 模型名称
            messages: 聊天消息列表
            temperature: 温度参数
            **kwargs: 其他模型特定参数

        Yields:
            str: SSE 格式的数据块

        Raises:
            ValueError: 如果模型名称不支持
        """
        try:
            service = ChatService.create_model_service(model)
            async for chunk in service.stream_chat_completions(
                messages=messages, temperature=temperature, **kwargs
            ):
                yield chunk
        except ValueError as e:
            logger.error(f"Model service error: {e}")
            yield f"data: {str(e)}\n\n"
        except asyncio.CancelledError:
            # 让 CancelledError 传播，不要吞掉它
            raise
        except Exception as e:
            logger.error(f"Unexpected error in chat service: {e}", exc_info=True)
            yield f"data: {str(e)}\n\n"
