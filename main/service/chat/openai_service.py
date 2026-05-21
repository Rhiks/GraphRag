"""
OpenAI 格式模型服务（统一接口实现）
适用于所有通过 one_api 等统一接口访问的模型
"""

import json
from typing import AsyncIterator, List, Optional, Dict, Any

import httpx

from config.logger import logger
from robot_warning import send_wechat_message
from model.chat import ChatMessage
import pdb


class OpenAIService:
    """
    OpenAI 格式模型服务实现

    适用于所有使用 OpenAI 格式接口的模型服务（包括通过 one_api 统一接口访问的模型）
    所有模型都使用相同的调用逻辑，仅模型名称和配置不同
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        初始化服务

        Args:
            model_name: 模型名称
            api_key: API 密钥
            base_url: API 基础 URL，默认为 OpenAI 官方地址
        """
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key

        logger.info(
            f"Initialized OpenAIService: {self.model_name}, base_url: {self.base_url}"
        )

        if not self.api_key:
            raise ValueError("API key is required")

    async def stream_chat_completions(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        流式生成聊天完成响应（OpenAI 格式）

        Args:
            messages: 聊天消息列表
            temperature: 温度参数
            **kwargs: 其他模型特定参数

        Yields:
            str: SSE 格式的数据块
        """
        # 转换消息格式为 OpenAI 格式
        openai_messages = self._convert_messages(messages)

        # 构建请求体（OpenAI 格式）
        request_body = {
            "model": self.model_name,
            "messages": openai_messages,
            "stream": True,
        }

        if temperature is not None:
            request_body["temperature"] = temperature

        # 合并其他参数
        request_body.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            url = self.base_url.rstrip("/") + "/v1/chat/completions"
            logger.info(f"Streaming request to {url} with model {self.model_name}")

            # 打印完整的请求信息用于调试
            logger.debug(f"Request URL: {url}")
            logger.debug(
                f"Request Headers: {json.dumps({k: v if k != 'Authorization' else 'Bearer ***' for k, v in headers.items()}, indent=2, ensure_ascii=False)}"
            )
            logger.debug(
                f"Request Body: {json.dumps(request_body, indent=2, ensure_ascii=False)}"
            )

            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers=headers,
                    json=request_body,
                ) as response:
                    logger.info(
                        f"API response status: {response.status_code} for {self.model_name}"
                    )
                    if response.status_code != 200:
                        error_text = await response.aread()
                        error_msg = error_text.decode()
                        error_message = f"API error ({self.model_name}): {response.status_code}, messages: {json.dumps(request_body['messages'], indent=2, ensure_ascii=False)}, {error_msg}"
                        logger.error(error_message)
                        #pdb.set_trace() 
                        send_wechat_message(error_message)
                        yield self._format_sse_data(
                            json.dumps({"error": f"API error: {response.status_code}"})
                        )
                        return

                    chunk_count = 0
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        # OpenAI 流式响应格式: data: {...}\n\n
                        # 直接转发，不做解析
                        if line.startswith("data: "):
                            data_str = line[6:]  # 移除 "data: " 前缀
                            if data_str.strip() == "[DONE]":
                                logger.info(
                                    f"Stream completed for {self.model_name}, total chunks: {chunk_count}"
                                )
                                yield self._format_sse_done()
                                break

                            # 直接转发原始数据，不做解析
                            chunk_count += 1
                            yield self._format_sse_data(data_str)

        except Exception as e:
            logger.error(f"Error calling API ({self.model_name}): {e}", exc_info=True)
            yield self._format_sse_data(
                json.dumps({"error": f"Service error: {str(e)}"})
            )

    def _format_sse_data(self, content: str) -> str:
        """
        格式化 SSE 数据

        Args:
            content: 内容字符串

        Returns:
            str: SSE 格式的数据
        """
        return f"data: {content}\n\n"

    def _format_sse_done(self) -> str:
        """
        格式化 SSE 结束标记

        Returns:
            str: SSE 结束标记
        """
        return "data: [DONE]\n\n"

    def _convert_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """
        转换消息格式为 OpenAI 格式

        Args:
            messages: ChatMessage 列表

        Returns:
            List[Dict]: 转换后的消息列表
        """
        result = []
        for msg in messages:
            message_dict = {
                "role": msg.role,
                "content": msg.content,
            }
            result.append(message_dict)
        return result

    async def create_chat_completions(
        self,
        messages: List[ChatMessage],
        temperature: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        生成聊天完成响应（非流式）

        Args:
            messages: 聊天消息列表
            temperature: 温度参数
            **kwargs: 其他模型特定参数

        Returns:
            Dict[str, Any]: 模型响应
        """
        # 转换消息格式为 OpenAI 格式
        openai_messages = self._convert_messages(messages)

        # 构建请求体（OpenAI 格式）
        request_body = {
            "model": self.model_name,
            "messages": openai_messages,
            "stream": False,
        }

        if temperature is not None:
            request_body["temperature"] = temperature

        # 合并其他参数
        request_body.update(kwargs)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            url = self.base_url.rstrip("/") + "/v1/chat/completions"
            logger.info(f"Request to {url} with model {self.model_name}")

            # 打印完整的请求信息用于调试
            logger.debug(f"Request URL: {url}")
            logger.debug(
                f"Request Headers: {json.dumps({k: v if k != 'Authorization' else 'Bearer ***' for k, v in headers.items()}, indent=2, ensure_ascii=False)}"
            )
            logger.debug(
                f"Request Body: {json.dumps(request_body, indent=2, ensure_ascii=False)}"
            )

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=request_body,
                )

                logger.info(
                    f"API response status: {response.status_code} for {self.model_name}"
                )
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_msg = error_text.decode()
                    error_message = f"API error ({self.model_name}): {response.status_code}, messages: {json.dumps(request_body['messages'], indent=2, ensure_ascii=False)}, {error_msg}"
                    logger.error(error_message)
                    send_wechat_message(error_message)
                    return {"error": f"API error: {response.status_code}"}

                # 解析响应
                result = response.json()
                logger.debug(f"API response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result

        except Exception as e:
            logger.error(f"Error calling API ({self.model_name}): {e}", exc_info=True)
            return {"error": f"Service error: {str(e)}"}
