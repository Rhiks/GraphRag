"""
SSE (Server-Sent Events) 格式处理工具
"""

import json
from typing import List

from config.logger import logger


class SSEHandler:
    """SSE格式处理工具类"""

    @staticmethod
    def extract_content_from_chunk(chunk: str) -> str:
        """
        从单个 SSE 格式的 chunk 中提取 content

        Args:
            chunk: SSE 格式的数据块，例如 "data: {...}\n\n"

        Returns:
            str: 提取的 content，如果无法提取则返回空字符串
        """
        # SSE 格式: data: {...}\n\n
        if not chunk.startswith("data: "):
            return ""

        data_str = chunk[6:].strip()  # 移除 "data: " 前缀
        if not data_str or data_str == "[DONE]":
            return ""

        try:
            # 尝试解析 JSON
            data = json.loads(data_str)
            # OpenAI 格式: {"choices": [{"delta": {"content": "..."}}]}
            if isinstance(data, dict) and "choices" in data:
                for choice in data.get("choices", []):
                    delta = choice.get("delta", {})
                    if "content" in delta:
                        return delta["content"]
            # 错误格式: {"error": "..."}
            elif isinstance(data, dict) and "error" in data:
                logger.warning(f"Error in SSE chunk: {data.get('error')}")
                return ""
        except json.JSONDecodeError:
            # 如果不是 JSON，可能是纯文本，直接使用
            if data_str:
                return data_str

        return ""

    @staticmethod
    def parse_sse_content(chunks: List[str]) -> str:
        """
        从 SSE 格式的 chunks 中提取完整响应文本

        Args:
            chunks: SSE 格式的数据块列表

        Returns:
            str: 完整的响应文本
        """
        content_parts = []
        for chunk in chunks:
            content = SSEHandler.extract_content_from_chunk(chunk)
            if content:
                content_parts.append(content)

        return "".join(content_parts)

    @staticmethod
    def format_judge_result_sse(content: str) -> str:
        """
        格式化批改结果为SSE格式

        Args:
            content: 批改结果文本

        Returns:
            str: SSE格式的数据
        """
        # 将文本内容格式化为JSON格式的SSE数据
        data = {"choices": [{"delta": {"content": content}}]}
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
