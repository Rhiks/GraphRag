from typing import Optional

from pydantic import BaseModel, Field


class StudentRequest(BaseModel):
    student_user_id: int = Field(..., description="学生用户 id")
    student_name: Optional[str] = Field(None, description="学生姓名")
    phone: Optional[str] = Field(None, description="电话号码")
