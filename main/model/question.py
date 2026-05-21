from typing import Optional, Union

from pydantic import BaseModel, Field


class QuestionPart(BaseModel):
    fragment_id: Optional[str] = Field(None, description="题目片段 id")
    html: Optional[str] = Field(None, description="题目片段 html 内容")
    text: Optional[str] = Field(None, description="题目内容")


class TopicRequest(BaseModel):
    topic_id: int = Field(..., description="题目 id")
    topic_type: int = Field(
        ..., description="题目类型(1:选择题,2:填空题,3:判断题,4:解答题,5:综合题)"
    )
    sub_index: Optional[int] = Field(None, description="子题下标(0-based), 综合题必传")
    stem: Optional[QuestionPart] = Field(None, description="题干内容")
    answers: Optional[list[QuestionPart]] = Field(None, description="答案内容")
    jiexis: Optional[list[QuestionPart]] = Field(None, description="解析内容")
    options: Optional[list[QuestionPart]] = Field(None, description="选项 (仅选择题)")
    subject_product_id: Optional[int] = Field(
        None, description="学科 id", examples=[214]
    )


class QuestionRequest(BaseModel):
    topic_info: TopicRequest
    question_id: Optional[int] = Field(None, description="学生作答 id")
    img_url: Union[str, list[str]] = Field(
        ...,
        description="学生作答图片 URL；主观题可为多张（列表），客观题为单张字符串或列表（列表时取首张）",
    )
