from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from model.question import QuestionRequest
from model.student import StudentRequest
from model.chat import ChatMessage


class JudgeRequest(BaseModel):
    student_info: StudentRequest
    question_info: QuestionRequest
    conversation_id: str
    request_id: Optional[str] = Field(None, description="请求ID，由服务端生成")
    page_source: int = Field(
        0, description="页面来源，对应原接口的 question_params.from 字段"
    )


# 状态码常量
STATUS_NORMAL = 0
STATUS_ERROR = 1


class CommonJudgeResponse(BaseModel):
    """通用判题响应模型"""

    conversation_id: str = Field(..., alias="conversationId", description="会话ID")
    is_finished: bool = Field(..., alias="isFinished", description="是否完成")
    index: int = Field(..., description="索引，递增")
    message: ChatMessage = Field(..., description="消息")
    code: int = Field(
        default=0, description="状态码，0=正常，1=错误"
    )  # 对应 Java 的 STATUS_NORMAL
    error_message: Optional[str] = Field(
        default=None, alias="errorMessage", description="错误消息"
    )

    model_config = ConfigDict(
        populate_by_name=True,  # 允许同时使用字段名和别名
    )
