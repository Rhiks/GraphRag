"""
OCR 处理器
负责图像裁剪、OCR 识别等后处理操作
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path
import concurrent.futures
from .ocr_clients import LocalPaddleOcrClient, OcrBlanksRecogClient, is_finite_number
import pdb


class ImageMismatchError(Exception):
    """图片错误异常：当识别框数量与标准答案数量不匹配时抛出"""
    pass



class OcrProcessor:
    """
    OCR 处理器
    提供图像裁剪、识别等功能
    """
    
    def __init__(self, 
                 local_paddle_ocr_client: LocalPaddleOcrClient,
                 ocr_blanks_recog_client: OcrBlanksRecogClient,
                 debug: bool = False,
                 debug_dir: Optional[Path] = None):
        """
        初始化 OCR 处理器
        
        Args:
            local_paddle_ocr_client: 纯数字 OCR 客户端
            ocr_blanks_recog_client: 全能 OCR 客户端
            debug: 是否启用调试模式
            debug_dir: 调试文件保存目录
        """
        self.local_paddle_ocr_client = local_paddle_ocr_client
        self.ocr_blanks_recog_client = ocr_blanks_recog_client
        self.debug = debug
        self.debug_dir = debug_dir
    
    def recognize(self,
                  image: np.ndarray,
                  boxes: List[Tuple[int, int, int, int]],
                  es_answers: List[str],
                  question_params: Dict[str, Any]) -> List[str]:
        """
        识别填空区域
        
        处理流程：
        1. 根据检测框裁剪图像
        2. 根据标准答案判断使用哪种 OCR
        3. 并发识别所有填空
        4. 返回识别结果列表
        
        Args:
            image: 输入图像
            boxes: 检测框列表，每个框格式为 (x1, y1, x2, y2)
            es_answers: 标准答案列表
            question_params: 题目参数
            
        Returns:
            识别结果列表
        """
        if not boxes:
            return []
        
        # 如果标准答案数量与检测框数量不匹配，说明提交的图片错误，抛出异常
        if len(es_answers) != len(boxes):
            raise ImageMismatchError(
                f"识别框数量({len(boxes)})与标准答案数量({len(es_answers)})不匹配，"
                f"说明提交的图片错误"
            )
        
        # 裁剪图像
        cropped_images = self._crop_images(image, boxes)
        
        # 并发识别
        results = self._recognize_concurrent(cropped_images, es_answers, question_params)
        
        return results
    
    def _crop_images(self, 
                     image: np.ndarray, 
                     boxes: List[Tuple[int, int, int, int]]) -> List[bytes]:
        """
        根据检测框裁剪图像
        
        Args:
            image: 输入图像
            boxes: 检测框列表，每个框格式为 (x1, y1, x2, y2)
            
        Returns:
            裁剪后的图像字节数据列表
        """
        cropped_images = []
        
        # Debug: 创建保存裁剪图像的目录
        if self.debug and self.debug_dir:
            ocr_cropped_dir = self.debug_dir / "05a_ocr_cropped_images"
            ocr_cropped_dir.mkdir(exist_ok=True)
        
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box
            
            # 裁剪图像
            roi = image[y1:y2, x1:x2]
            
            # Debug: 保存裁剪的图像
            if self.debug and self.debug_dir:
                box_path = ocr_cropped_dir / f"ocr_box_{i+1:02d}_({x1},{y1},{x2},{y2}).jpg"
                cv2.imwrite(str(box_path), roi)
                if i == 0:
                    print(f"[DEBUG] 开始保存OCR裁剪图像到: {ocr_cropped_dir}")
            
            # 编码为 JPEG 字节数据
            success, encoded_image = cv2.imencode('.jpg', roi)
            if success:
                cropped_images.append(encoded_image.tobytes())
            else:
                # 编码失败，添加空字节
                cropped_images.append(b'')
                if self.debug:
                    print(f"[DEBUG] 警告: 框 {i+1} 图像编码失败")
        
        if self.debug and self.debug_dir:
            print(f"[DEBUG] 已保存 {len(cropped_images)} 个OCR裁剪图像到: {ocr_cropped_dir}")
        
        return cropped_images
    
    def _recognize_single(self, 
                         image_data: bytes, 
                         answer: str, 
                         question_params: Dict[str, Any],
                         index: int) -> str:
       
        """
        识别单个填空区域
        
        Args:
            image_data: 图像字节数据
            answer: 对应的标准答案
            question_params: 题目参数
            index: 填空序号
            
        Returns:
            识别结果文本
        """
        if not image_data:
            return ""
        
        try:
            #pdb.set_trace()
            # 判断是否为纯数字
            if is_finite_number(answer):
                # 使用纯数字 OCR
                result = self.local_paddle_ocr_client.recognize(image_data)
                print(f"{index}_result: {result}")
                return result.text
            else:
                # 使用全能 OCR
                result = self.ocr_blanks_recog_client.recognize(
                    image_data, answer, question_params, index
                )
                if result.code == 200:
                    print(f"{index}_result: {result.latex_string}")
                    return result.latex_string
                else:
                    # OCR 失败，返回空字符串
                    return ""
        except Exception as e:
            # 识别异常，返回空字符串
            print(f"OCR 识别异常 (index={index}): {str(e)}")
            return ""
    
    def _recognize_concurrent(self, 
                             cropped_images: List[bytes],
                             es_answers: List[str],
                             question_params: Dict[str, Any]) -> List[str]:
        """
        并发识别多个填空区域
        
        Args:
            cropped_images: 裁剪后的图像字节数据列表
            es_answers: 标准答案列表
            question_params: 题目参数
            
        Returns:
            识别结果列表
        """
        results = []
        
        # 使用线程池并发识别
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(cropped_images)) as executor:
            # 提交所有识别任务
            futures = []
            for index, (image_data, answer) in enumerate(zip(cropped_images, es_answers)):
                future = executor.submit(
                    self._recognize_single,
                    image_data,
                    answer,
                    question_params,
                    index
                )
                futures.append(future)
            
            # 获取所有结果
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"获取 OCR 结果异常: {str(e)}")
                    results.append("")
        
        return results
