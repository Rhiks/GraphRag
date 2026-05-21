"""
聊天相关数据模型
"""

from typing import List, Optional, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色，如 'user', 'assistant', 'system'")
    content: Any = Field(..., description="消息内容")


class ChatCompletionRequest(BaseModel):
    model: str = Field(..., description="模型名称")
    messages: List[ChatMessage] = Field(..., description="聊天消息列表", min_length=1)
    temperature: Optional[float] = Field(0.2, description="温度参数")
