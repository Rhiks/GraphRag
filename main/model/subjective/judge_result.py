"""
判题结果相关的数据类和枚举
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class ScoreRange(Enum):
    """分数区间枚举"""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class JudgeResult:
    """判题结果"""

    template_id: str
    model: str
    full_response: str
    chunks: List[str]  # 收集的所有流式数据块
    score: Optional[float] = None  # 解析出的得分（0.0-1.0）
    subject_product_id: Optional[int] = None  # 学科产品ID
    last_index: int = -1  # 最后索引（用于标识是否成功，> -1表示成功）
