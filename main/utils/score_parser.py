"""
得分解析和结果计算工具
"""

import re
from typing import Optional

from config.logger import logger
from model.subjective.judge_result import ScoreRange


class ScoreParser:
    """得分解析和结果计算工具类"""

    @staticmethod
    def parse_score(content: str) -> Optional[float]:
        """
        从响应内容中解析得分

        通过正则表达式提取"得分：** {分数}"格式的得分

        Args:
            content: 完整的响应文本

        Returns:
            Optional[float]: 解析出的得分（0.0-1.0），如果解析失败返回 None
        """
        # 匹配 "得分：** {分数}" 或 "得分：{分数}" 等格式
        # 支持多种可能的格式变体
        patterns = [
            r"\*\*得分：\*\*\s*([0-9.]+)",  # **得分：** 0.8
            r"得分：\*\*\s*([0-9.]+)",  # 得分：** 0.8
            r"\*\*得分：\s*([0-9.]+)",  # **得分： 0.8
            r"得分：\s*([0-9.]+)",  # 得分： 0.8
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    score = float(match.group(1))
                    # 确保得分在 0.0-1.0 范围内
                    if 0.0 <= score <= 1.0:
                        return score
                    elif score > 1.0:
                        # 如果得分大于1.0，可能是百分比格式（如80表示0.8）
                        return min(score / 100.0, 1.0)
                    else:
                        logger.warning(
                            f"Parsed score {score} is out of range, returning None"
                        )
                        return None
                except ValueError:
                    continue

        logger.warning(f"Could not parse score from content: {content[:200]}")
        return None

    @staticmethod
    def calculate_judge_result(score: float) -> int:
        """
        根据得分计算批改结果

        Args:
            score: 得分（0.0-1.0）

        Returns:
            int: 批改结果（0-答错，1-答对，2-部分正确）
        """
        if score >= 1.0:
            return 1  # 答对
        elif score > 0.0:
            return 2  # 部分正确
        else:
            return 0  # 答错

    @staticmethod
    def classify_score_range(
        score: float, subject_product_id: Optional[int]
    ) -> ScoreRange:
        """
        根据得分和学科产品ID分类分数区间

        Args:
            score: 得分（0.0-1.0）
            subject_product_id: 学科产品ID

        Returns:
            ScoreRange: 分数区间
        """
        # 物理学科（subjectProductId=214）使用不同的阈值
        if subject_product_id == 214:
            if score >= 1.0:
                return ScoreRange.HIGH
            elif score >= 0.3:
                return ScoreRange.MEDIUM
            else:
                return ScoreRange.LOW
        else:
            # 其他学科
            if score >= 0.8:
                return ScoreRange.HIGH
            elif score >= 0.3:
                return ScoreRange.MEDIUM
            else:
                return ScoreRange.LOW
