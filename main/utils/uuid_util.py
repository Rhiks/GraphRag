"""
UUID 工具函数
"""

import uuid


def generate_uuid() -> str:
    """
    生成随机 UUID 字符串

    Returns:
        str: UUID 字符串，格式类似 "550e8400-e29b-41d4-a716-446655440000"
    """
    return str(uuid.uuid4())
