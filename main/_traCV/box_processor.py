"""
检测框处理器
负责检测框的过滤、排序等后处理操作
"""

from typing import List
from .layout_api_client import Box as LayoutBox


class BoxProcessor:
    """
    检测框处理器
    提供检测框的过滤、排序等功能
    """
    
    def __init__(self, 
                 coverage_threshold: float = 0.85,
                 area_ratio_threshold: float = 1.2,
                 min_box_area: int = 100,
                 same_line_overlap_threshold: float = 0.5):
        """
        初始化检测框处理器
        
        Args:
            coverage_threshold: 覆盖率阈值，判断包含关系，默认 0.85 (85%)
            area_ratio_threshold: 面积比阈值，区分包含/重复，默认 1.2
            min_box_area: 最小有效框面积（像素），过滤噪点，默认 100
            same_line_overlap_threshold: 同行判断的垂直重叠阈值，默认 0.5 (50%)
        """
        self.coverage_threshold = coverage_threshold
        self.area_ratio_threshold = area_ratio_threshold
        self.min_box_area = min_box_area
        self.same_line_overlap_threshold = same_line_overlap_threshold
    
    def process(self, boxes: List[LayoutBox]) -> List[LayoutBox]:
        """
        处理检测框：过滤 + 排序
        
        Args:
            boxes: 原始检测框列表
            
        Returns:
            处理后的检测框列表（已过滤和排序）
        """
        # 1. 过滤重叠框
        filtered_boxes = self.filter_overlapping_boxes(boxes)
        
        # 2. 按书写顺序排序
        sorted_boxes = self.sort_boxes_reading_order(filtered_boxes)
        
        return sorted_boxes
    
    def filter_overlapping_boxes(self, boxes: List[LayoutBox]) -> List[LayoutBox]:
        """
        过滤重叠的检测框，只保留较小的精准框
        
        核心策略：
        - 过滤掉明显无效的框（负坐标、面积为0、极小噪点）
        - 检测大框套小框的情况，删除大框保留小框
        - 检测重复识别的情况，删除较小的框
        
        Args:
            boxes: 原始检测框列表
            
        Returns:
            过滤后的检测框列表
        """
        if not boxes:
            return []
        
        # 步骤 1: 预处理 - 过滤掉明显无效的框
        valid_boxes = [box for box in boxes if self._is_valid_box(box)]
        
        # 按面积从小到大排序（优先处理小框）
        valid_boxes = sorted(valid_boxes, key=self._calculate_area)
        
        # 步骤 2: 标记需要删除的框
        boxes_to_remove = set()
        
        for i, box_a in enumerate(valid_boxes):
            if id(box_a) in boxes_to_remove:
                continue
            
            for j, box_b in enumerate(valid_boxes):
                if i == j or id(box_b) in boxes_to_remove:
                    continue
                
                # 检测并标记需要删除的框
                self._detect_and_mark_removals(box_a, box_b, boxes_to_remove)
        
        # 步骤 3: 返回未被标记删除的框
        return [box for box in valid_boxes if id(box) not in boxes_to_remove]
    
    def _detect_and_mark_removals(self, box_a: LayoutBox, box_b: LayoutBox, 
                                  remove_set: set) -> None:
        """
        检测两个框的关系，标记需要删除的框
        
        Args:
            box_a: 第一个框
            box_b: 第二个框
            remove_set: 存储需要删除的框ID的集合
        """
        area_a = self._calculate_area(box_a)
        area_b = self._calculate_area(box_b)
        intersection = self._calculate_intersection(box_a, box_b)
        
        # 如果没有交集，直接返回
        if intersection <= 0:
            return
        
        min_area = min(area_a, area_b)
        max_area = max(area_a, area_b)
        
        # 计算重叠部分占较小框的比例
        coverage_rate = intersection / min_area
        
        # 使用配置的阈值判断
        if coverage_rate > self.coverage_threshold:
            # 计算面积差异比例
            if max_area / min_area > self.area_ratio_threshold:
                # 包含关系：删除大框，保留小框
                if area_a > area_b:
                    remove_set.add(id(box_a))
                else:
                    remove_set.add(id(box_b))
            else:
                # 重复识别：删除面积较小的框
                if area_a < area_b:
                    remove_set.add(id(box_a))
                else:
                    remove_set.add(id(box_b))
    
    def sort_boxes_reading_order(self, boxes: List[LayoutBox]) -> List[LayoutBox]:
        """
        按照书写顺序排序检测框（从上到下，从左到右）
        
        策略：
        1. 先按 Y 坐标排序
        2. 将视觉上在同一行的框分组
        3. 每一行内按 X 坐标排序
        
        Args:
            boxes: 检测框列表
            
        Returns:
            排序后的检测框列表
        """
        if not boxes:
            return []
        
        # 1. 按 Y 坐标（top）排序
        sorted_boxes = sorted(boxes, key=lambda box: box.coordinate[1])
        
        # 2. 分行
        rows = []
        for current_box in sorted_boxes:
            if not rows:
                # 第一行
                rows.append([current_box])
                continue
            
            # 取出当前最后一行的最后一个元素作为参考
            last_row = rows[-1]
            row_ref = last_row[-1]
            
            # 判断是否在同一行
            if self._is_same_line(row_ref, current_box):
                last_row.append(current_box)
            else:
                # 新建一行
                rows.append([current_box])
        
        # 3. 每一行内按 X 坐标排序
        result = []
        for row in rows:
            row.sort(key=lambda box: box.coordinate[0])
            result.extend(row)
        
        return result
    
    def _is_same_line(self, box1: LayoutBox, box2: LayoutBox) -> bool:
        """
        判断两个框是否在视觉上的同一行
        
        使用垂直重叠率判断：如果重叠高度超过较小框高度的阈值，
        则认为在同一行
        
        Args:
            box1: 第一个框
            box2: 第二个框
            
        Returns:
            True 表示在同一行，False 表示不在同一行
        """
        # coordinate 格式: [x1, y1, x2, y2]
        y1_top = box1.coordinate[1]
        y1_bottom = box1.coordinate[3]
        h1 = y1_bottom - y1_top
        
        y2_top = box2.coordinate[1]
        y2_bottom = box2.coordinate[3]
        h2 = y2_bottom - y2_top
        
        # 计算垂直重叠区域
        overlap_top = max(y1_top, y2_top)
        overlap_bottom = min(y1_bottom, y2_bottom)
        overlap_height = max(0, overlap_bottom - overlap_top)
        
        # 取较小的高度作为分母
        min_height = min(h1, h2)
        
        # 使用配置的阈值判断
        return overlap_height > (min_height * self.same_line_overlap_threshold)
    
    def _is_valid_box(self, box: LayoutBox) -> bool:
        """
        验证检测框是否有效
        
        过滤条件：
        - 坐标格式正确
        - 坐标方向正确（右>左，下>上）
        - 面积不能太小（过滤噪点）
        
        Args:
            box: 检测框
            
        Returns:
            True 表示有效，False 表示无效
        """
        if not box.coordinate or len(box.coordinate) != 4:
            return False
        
        x1, y1, x2, y2 = box.coordinate
        
        # 坐标方向校验
        if x2 <= x1 or y2 <= y1:
            return False
        
        # 噪点过滤：面积小于配置的最小面积
        area = (x2 - x1) * (y2 - y1)
        if area < self.min_box_area:
            return False
        
        return True
    
    @staticmethod
    def _calculate_area(box: LayoutBox) -> int:
        """
        计算检测框的面积
        
        Args:
            box: 检测框
            
        Returns:
            面积（像素数）
        """
        x1, y1, x2, y2 = box.coordinate
        return (x2 - x1) * (y2 - y1)
    
    @staticmethod
    def _calculate_intersection(box_a: LayoutBox, box_b: LayoutBox) -> int:
        """
        计算两个检测框的交集面积
        
        Args:
            box_a: 第一个框
            box_b: 第二个框
            
        Returns:
            交集面积（像素数）
        """
        x1_a, y1_a, x2_a, y2_a = box_a.coordinate
        x1_b, y1_b, x2_b, y2_b = box_b.coordinate
        
        # 计算交集矩形的坐标
        x_overlap = max(0, min(x2_a, x2_b) - max(x1_a, x1_b))
        y_overlap = max(0, min(y2_a, y2_b) - max(y1_a, y1_b))
        
        return x_overlap * y_overlap
