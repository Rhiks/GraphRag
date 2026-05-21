"""
结果选举逻辑
"""

from typing import Dict, Optional

from config.logger import logger
from model.subjective.judge_result import JudgeResult, ScoreRange
from utils.score_parser import ScoreParser


class ResultElector:
    """结果选举器"""

    @staticmethod
    def elect_best_result(
        results: Dict[str, JudgeResult], subject_product_id: Optional[int]
    ) -> Optional[JudgeResult]:
        """
        选举最佳判题结果（投票机制）

        算法：
        1. 按分数区间分类（HIGH/MEDIUM/LOW）
        2. 选择最多投票的区间
        3. 在选中区间内选择最高分

        Args:
            results: 所有判题结果
            subject_product_id: 学科产品ID

        Returns:
            Optional[JudgeResult]: 选中的最佳结果，如果为空则返回 None
        """
        if not results:
            return None

        # 1. 结果过滤：过滤出成功的结果（lastIndex > -1 且 score 不为 None）
        valid_results = [
            result
            for result in results.values()
            if result.last_index > -1 and result.score is not None
        ]

        if not valid_results:
            logger.warning("No valid results with score available")
            return None

        # 2. 按分数区间分类
        range_results: Dict[ScoreRange, list[JudgeResult]] = {
            ScoreRange.HIGH: [],
            ScoreRange.MEDIUM: [],
            ScoreRange.LOW: [],
        }

        for result in valid_results:
            score_range = ScoreParser.classify_score_range(
                result.score, result.subject_product_id or subject_product_id
            )
            range_results[score_range].append(result)

        # 3. 选择最多投票的区间
        # 统计每个区间的结果数量
        range_counts = {
            range_type: len(results_list)
            for range_type, results_list in range_results.items()
        }

        # 选择结果数量最多的区间
        max_count = max(range_counts.values())
        selected_ranges = [
            range_type
            for range_type, count in range_counts.items()
            if count == max_count
        ]

        # 如果数量相同，优先选择等级更高的区间（HIGH > MEDIUM > LOW）
        priority_order = [ScoreRange.HIGH, ScoreRange.MEDIUM, ScoreRange.LOW]
        selected_range = None
        for range_type in priority_order:
            if range_type in selected_ranges:
                selected_range = range_type
                break

        if selected_range is None:
            logger.error("Failed to select score range")
            # 降级：返回第一个有效结果（确保列表不为空）
            if valid_results:
                return valid_results[0]
            else:
                logger.error("No valid results available for fallback")
                return None

        candidates = range_results[selected_range]
        logger.info(
            f"Selected range: {selected_range.value}, "
            f"count: {len(candidates)}, "
            f"total valid results: {len(valid_results)}"
        )

        # 确保候选列表不为空
        if not candidates:
            logger.error(f"Selected range {selected_range.value} has no candidates")
            # 降级：返回第一个有效结果
            if valid_results:
                return valid_results[0]
            else:
                return None

        # 4. 在选中区间内选择最高分
        best_result = max(candidates, key=lambda r: r.score)
        logger.info(
            f"Elected best result: template_id={best_result.template_id}, "
            f"score={best_result.score}, range={selected_range.value}"
        )

        return best_result
