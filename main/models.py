#-*- coding: utf-8 -*-
"""
Pydantic models for request and response validation
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class QuestionParams(BaseModel):
    """Question parameters model"""
    model_config = ConfigDict(populate_by_name=True)  # Allow both "from" and "page_source"
    
    student_user_id: str
    topic_id: str
    topic_type: str
    question_id: Optional[int] = Field(default=-1)
    page_source: Optional[int] = Field(default=0, alias="from")


class QuestionInfo(BaseModel):
    """Question info model"""
    es_answers: str
    stem: str


class BlanksRecogRequest(BaseModel):
    """Blanks recognition request model"""
    img_url: str
    question_params: QuestionParams
    question_info: QuestionInfo


class TokenRequest(BaseModel):
    """Token request model"""
    username: str
    password: str


class HealthResponse(BaseModel):
    """Health check response model"""
    Msg: str = "success"


class TokenResponse(BaseModel):
    """Token response model"""
    status_code: int
    message: str
    token: Optional[str] = None
    expires_in: Optional[int] = None


class ErrorResponse(BaseModel):
    """Error response model"""
    status_code: int
    message: str


class BlanksRecogResponse(BaseModel):
    """Blanks recognition response model"""
    status_code: int
    message: str
    request_id: str
    recog_results: Dict[str, Any] = Field(default_factory=dict)
