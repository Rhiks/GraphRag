import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import os
from datetime import datetime
import json
from .layout_api_client import LayoutAPIClient
from .box_processor import BoxProcessor
from .ocr_clients import LocalPaddleOcrClient, OcrBlanksRecogClient
from .ocr_processor import OcrProcessor

# 尝试导入 logger，如果失败则使用 print
try:
    from ..config.logger import logger
except ImportError:
    try:
        from config.logger import logger
    except ImportError:
        import logging
        logger = logging.getLogger(__name__)


class TraditionalCV:
    """
    传统计算机视觉处理类
    包含布局检测、OCR识别等功能的完整流程
    """
    
    def __init__(self, layout_model_path: Optional[str] = None, 
                 ocr_model_path: Optional[str] = None,
                 layout_api_url: Optional[str] = None,
                 layout_threshold: float = 0.3,
                 local_paddle_ocr_url: Optional[str] = None,
                 ocr_blanks_recog_url: Optional[str] = None,
                 Layout_choice_api_url: Optional[str] = None,
                 debug: bool = False,
                 debug_dir: Optional[str] = None):
        """
        初始化 TraditionalCV 类
        
        Args:
            layout_model_path: layout 检测模型的路径（已弃用，改用 API）
            ocr_model_path: OCR 识别模型的路径（已弃用，改用 API）
            layout_api_url: Layout API 的 URL
            layout_threshold: Layout 检测阈值，默认 0.3
            local_paddle_ocr_url: 纯数字 OCR API 的 URL
            ocr_blanks_recog_url: 全能 OCR API 的 URL
            debug: 是否启用调试模式，默认 False
            debug_dir: 调试文件保存目录，如果为 None 则使用默认目录
        """
        # Debug 模式设置
        self.debug = debug
        if debug:
            if debug_dir:
                self.debug_dir = Path(debug_dir)
            else:
                # 默认使用项目根目录下的 debug_output 目录
                project_root = Path(__file__).parent.parent.parent.parent
                self.debug_dir = project_root / "debug_output"
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            # 为每次运行创建时间戳子目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.debug_dir = self.debug_dir / timestamp
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            print(f"[DEBUG] 调试模式已启用，输出目录: {self.debug_dir}")
        else:
            self.debug_dir = None
        # 初始化 Layout API 客户端
        if layout_api_url:
            self.layout_api_client = LayoutAPIClient(layout_api_url, layout_threshold)
        else:
            # 从配置文件读取
            try:
                from ..config.config import Config
                # 使用 Config.LAYOUT_API_URL 属性，它已经有默认值
                api_url = Config.LAYOUT_API_URL
                if api_url:
                    self.layout_api_client = LayoutAPIClient(api_url, layout_threshold)
                else:
                    self.layout_api_client = None
            except (ImportError, AttributeError):
                self.layout_api_client = None
        
        # 初始化检测框处理器
        self.box_processor = BoxProcessor()
        
        # 初始化纯数字 OCR 客户端
        if local_paddle_ocr_url:
            self.local_paddle_ocr_client = LocalPaddleOcrClient(local_paddle_ocr_url)
        else:
            # 从配置文件读取
            try:
                from ..config.config import Config
                # 使用 Config.LOCAL_PADDLE_OCR_URL 属性，它已经有默认值
                ocr_url = Config.LOCAL_PADDLE_OCR_URL
                if ocr_url:
                    self.local_paddle_ocr_client = LocalPaddleOcrClient(ocr_url)
                else:
                    self.local_paddle_ocr_client = None
            except (ImportError, AttributeError):
                self.local_paddle_ocr_client = None
        
        # 初始化全能 OCR 客户端
        if ocr_blanks_recog_url:
            self.ocr_blanks_recog_client = OcrBlanksRecogClient(ocr_blanks_recog_url)
        else:
            # 从配置文件读取
            try:
                from ..config.config import Config
                # 使用 Config.OCR_BLANKS_RECOG_URL 属性，它已经有默认值
                ocr_url = Config.OCR_BLANKS_RECOG_URL
                if ocr_url:
                    self.ocr_blanks_recog_client = OcrBlanksRecogClient(ocr_url)
                else:
                    self.ocr_blanks_recog_client = None
            except (ImportError, AttributeError):
                self.ocr_blanks_recog_client = None
        
        # 初始化 OCR 处理器
        if self.local_paddle_ocr_client and self.ocr_blanks_recog_client:
            self.ocr_processor = OcrProcessor(
                self.local_paddle_ocr_client,
                self.ocr_blanks_recog_client,
                debug=self.debug,
                debug_dir=self.debug_dir
            )
        else:
            self.ocr_processor = None
            
        # 初始化选择题layout客户端
        if Layout_choice_api_url:
            self.layout_choice_api_client = LayoutAPIClient(Layout_choice_api_url, layout_threshold)
        else:
            # 从配置文件读取
            try:
                from ..config.config import Config
                # 使用 Config.LAYOUT_CHOICE_API_URL 属性
                api_url = Config.LAYOUT_CHOICE_API_URL
                if api_url:
                    self.layout_choice_api_client = LayoutAPIClient(api_url, layout_threshold)
                else:
                    self.layout_choice_api_client = None
            except (ImportError, AttributeError):
                self.layout_choice_api_client = None

        
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        图像预处理
        
        Args:
            image: 输入图像 (BGR格式)
            
        Returns:
            预处理后的图像
        """
        # TODO: 实现图像预处理逻辑
        # 例如：灰度化、尺寸调整、归一化等
        pass
    
    def _draw_boxes_on_image(self, image: np.ndarray, boxes: List[Tuple[int, int, int, int]], 
                             labels: Optional[List[str]] = None, 
                             colors: Optional[List[Tuple[int, int, int]]] = None) -> np.ndarray:
        """
        在图像上绘制检测框
        
        Args:
            image: 输入图像
            boxes: 检测框列表，格式为 (x1, y1, x2, y2)
            labels: 可选的标签列表
            colors: 可选的颜色列表，如果为None则使用默认颜色（不同框使用不同颜色）
            
        Returns:
            绘制了检测框的图像副本
        """
        result_image = image.copy()
        
        if colors is None:
            # 生成不同颜色，使用HSV色彩空间生成均匀分布的颜色
            colors = []
            for i in range(len(boxes)):
                hue = int(180 * i / max(len(boxes), 1))  # 0-180
                # 转换为BGR
                color_hsv = np.uint8([[[hue, 255, 255]]])
                color_bgr = cv2.cvtColor(color_hsv, cv2.COLOR_HSV2BGR)[0][0]
                colors.append(tuple(int(c) for c in color_bgr))
        
        for i, (x1, y1, x2, y2) in enumerate(boxes):
            color = colors[i % len(colors)]
            # 绘制矩形框
            cv2.rectangle(result_image, (x1, y1), (x2, y2), color, 2)
            
            # 如果有标签，在框的上方绘制标签
            if labels and i < len(labels):
                label = labels[i]
                # 计算文本大小
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.6
                thickness = 2
                (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, thickness)
                
                # 绘制文本背景
                cv2.rectangle(result_image, 
                            (x1, y1 - text_height - baseline - 5),
                            (x1 + text_width, y1),
                            color, -1)
                
                # 绘制文本
                cv2.putText(result_image, label, (x1, y1 - baseline - 5),
                          font, font_scale, (255, 255, 255), thickness)
        
        return result_image
    
    def get_detection_boxes(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        调用 Layout API，获取填空区域检测框，并进行过滤和排序
        
        处理流程：
        1. 将图像编码为字节数据
        2. 调用 Layout API 获取检测框
        3. 过滤重叠的检测框（保留较小的精准框）
        4. 按照书写顺序排序（从上到下，从左到右）
        
        Args:
            image: 输入图像 (numpy array, BGR格式)
            
        Returns:
            检测框列表，每个框格式为 (x1, y1, x2, y2)
            
        Raises:
            ValueError: 当 Layout API 客户端未初始化或 API 调用失败时
        """
        if self.layout_api_client is None:
            raise ValueError("Layout API 客户端未初始化，请提供 layout_api_url 或在配置中设置 LAYOUT_API_URL")
        
        # 1. 将图像编码为字节数据
        success, encoded_image = cv2.imencode('.jpg', image)
        if not success:
            raise ValueError("图像编码失败")
        
        image_bytes = encoded_image.tobytes()
        
        # Debug: 保存原始图像
        if self.debug:
            original_path = self.debug_dir / "01_original_image.jpg"
            cv2.imwrite(str(original_path), image)
            print(f"[DEBUG] 已保存原始图像: {original_path}")
        
        # 2. 调用 Layout API
        try:
            layout_result = self.layout_api_client.detect(image_bytes)
            if layout_result is None or not layout_result.boxes:
                if self.debug:
                    print(f"[DEBUG] Layout API 未检测到任何框")
                return []
        except Exception as e:
            raise ValueError(f"Layout API 调用失败: {str(e)}")
        
        # Debug: 保存原始检测框结果
        if self.debug:
            raw_boxes = [tuple(box.coordinate) for box in layout_result.boxes]
            raw_image = self._draw_boxes_on_image(image, raw_boxes, 
                                                 labels=[f"Box{i+1}" for i in range(len(raw_boxes))])
            raw_path = self.debug_dir / "02_raw_layout_boxes.jpg"
            cv2.imwrite(str(raw_path), raw_image)
            print(f"[DEBUG] 已保存原始Layout检测结果: {raw_path} (检测到 {len(raw_boxes)} 个框)")
        
        # 3. 使用 BoxProcessor 进行过滤和排序
        processed_boxes = self.box_processor.process(layout_result.boxes)
        
        # 4. 转换为 (x1, y1, x2, y2) 格式
        detection_boxes = [tuple(box.coordinate) for box in processed_boxes]
        
        # Debug: 保存处理后的检测框结果
        if self.debug:
            processed_image = self._draw_boxes_on_image(image, detection_boxes,
                                                       labels=[f"#{i+1}" for i in range(len(detection_boxes))])
            processed_path = self.debug_dir / "03_processed_layout_boxes.jpg"
            cv2.imwrite(str(processed_path), processed_image)
            print(f"[DEBUG] 已保存处理后的Layout检测结果: {processed_path} (处理后 {len(detection_boxes)} 个框)")
            
            # 保存每个检测框的裁剪图像
            boxes_dir = self.debug_dir / "04_detected_boxes"
            boxes_dir.mkdir(exist_ok=True)
            for i, (x1, y1, x2, y2) in enumerate(detection_boxes):
                box_image = image[y1:y2, x1:x2]
                box_path = boxes_dir / f"box_{i+1:02d}_({x1},{y1},{x2},{y2}).jpg"
                cv2.imwrite(str(box_path), box_image)
            print(f"[DEBUG] 已保存 {len(detection_boxes)} 个检测框的裁剪图像到: {boxes_dir}")
        
        return detection_boxes
    
    def thresh(self, image: np.ndarray, method: str = 'adaptive', 
               **kwargs) -> np.ndarray:
        """
        阈值处理
        
        Args:
            image: 输入图像（通常是灰度图）
            method: 阈值处理方法 ('adaptive', 'otsu', 'binary', 'binary_inv')
            **kwargs: 其他阈值处理参数
            
        Returns:
            二值化后的图像
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        if method == 'adaptive':
            # 自适应阈值
            block_size = kwargs.get('block_size', 11)
            C = kwargs.get('C', 2)
            thresh_img = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, block_size, C
            )
        elif method == 'otsu':
            # Otsu 阈值
            _, thresh_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif method == 'binary':
            # 固定阈值二值化
            threshold_value = kwargs.get('threshold_value', 127)
            _, thresh_img = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
        elif method == 'binary_inv':
            # 固定阈值二值化（反转）
            threshold_value = kwargs.get('threshold_value', 127)
            _, thresh_img = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY_INV)
        else:
            raise ValueError(f"Unsupported threshold method: {method}")
        
        return thresh_img
    
    def recognize(self, 
                  image: np.ndarray, 
                  boxes: List[Tuple[int, int, int, int]],
                  inference_params: Dict[str, Any]) -> List[str]:
        """
        调用 OCR 服务识别填空区域
        
        处理流程：
        1. 从 inference_params 中提取标准答案和题目参数
        2. 调用 OcrProcessor 进行识别
        3. 返回识别结果列表
        
        Args:
            image: 输入图像 (numpy array, BGR格式)
            boxes: 检测框列表，每个框格式为 (x1, y1, x2, y2)
            inference_params: 推理参数，包含 question_info 和 question_params
            
        Returns:
            识别结果列表，每个元素对应一个检测框的识别文本
            
        Raises:
            ValueError: 当 OCR 处理器未初始化时
        """
        if self.ocr_processor is None:
            raise ValueError("OCR 处理器未初始化，请提供 local_paddle_ocr_url 和 ocr_blanks_recog_url 或在配置中设置相应的 URL")
        
        if not boxes:
            return []
        
        # 提取标准答案和题目参数
        question_info = inference_params.get('question_info', {})
        question_params = inference_params.get('question_params', {})
        es_answers = question_info.get('es_answers', [])
        
        # Debug: 保存标准答案信息
        if self.debug:
            import json
            debug_info = {
                "es_answers": es_answers,
                "num_boxes": len(boxes),
                "boxes": boxes
            }
            info_path = self.debug_dir / "05_ocr_info.json"
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, ensure_ascii=False, indent=2)
            print(f"[DEBUG] 已保存OCR信息: {info_path}")
        
        # 使用 OcrProcessor 进行识别
        results = self.ocr_processor.recognize(image, boxes, es_answers, question_params)
        
        # Debug: 保存识别结果
        if self.debug:
            ocr_results = []
            for i, (box, result) in enumerate(zip(boxes, results)):
                ocr_results.append({
                    "box_index": i + 1,
                    "box": box,
                    "recognized_text": result,
                    "expected_answer": es_answers[i] if i < len(es_answers) else None,
                    "match": result.strip() == es_answers[i].strip() if i < len(es_answers) else False
                })
            
            results_path = self.debug_dir / "06_ocr_results.json"
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(ocr_results, f, ensure_ascii=False, indent=2)
            print(f"[DEBUG] 已保存OCR识别结果: {results_path}")
            
            # 在图像上绘制识别结果
            labels = []
            colors = []
            for i, (box, result) in enumerate(zip(boxes, results)):
                expected = es_answers[i] if i < len(es_answers) else "N/A"
                match = result.strip() == expected.strip() if i < len(es_answers) else False
                label = f"#{i+1}: {result}"
                if i < len(es_answers):
                    label += f" (期望: {expected})"
                    label += " ✓" if match else " ✗"
                labels.append(label)
                # 匹配用绿色，不匹配用红色
                colors.append((0, 255, 0) if match else (0, 0, 255))
            
            final_image = self._draw_boxes_on_image(image, boxes, labels=labels, colors=colors)
            final_path = self.debug_dir / "07_final_result.jpg"
            cv2.imwrite(str(final_path), final_image)
            print(f"[DEBUG] 已保存最终结果图像: {final_path}")
        
        return results
    
    def recognize_choice(self, bgr_im: np.ndarray, request_id: str = "") -> List[str]:
        """
        调用 layout_choice_api_client 检测选择题选项框，并返回去重后的 label 列表

        Args:
            bgr_im: 输入图像 (np.ndarray, BGR格式)
            request_id: 请求ID，用于日志记录

        Returns:
            List[str]: 按顺序去重后的检测到的 label 列表
        """
        # 验证输入图像
        if bgr_im is None:
            logger.error(f"{request_id}_recognize_choice: bgr_im 为 None")
            raise ValueError("输入图像 bgr_im 为 None")
        
        if not isinstance(bgr_im, np.ndarray):
            logger.error(f"{request_id}_recognize_choice: bgr_im 类型错误，期望 np.ndarray，实际 {type(bgr_im)}")
            raise ValueError(f"输入图像类型错误，期望 np.ndarray，实际 {type(bgr_im)}")
        
        logger.debug(f"{request_id}_recognize_choice: 输入图像尺寸 {bgr_im.shape}")
        
        # 检查 layout_choice_api_client 是否已初始化
        if self.layout_choice_api_client is None:
            logger.error(f"{request_id}_recognize_choice: layout_choice_api_client 未初始化")
            raise ValueError("Layout Choice API 客户端未初始化，请提供 Layout_choice_api_url 或在配置中设置 LAYOUT_CHOICE_API_URL")
        
        # 将图像编码为字节数据
        success, encoded_image = cv2.imencode('.jpg', bgr_im)
        if not success:
            logger.error(f"{request_id}_recognize_choice: 图像编码失败")
            raise ValueError("图像编码失败")
        image_bytes = encoded_image.tobytes()
        
        # 记录 API URL
        api_url = self.layout_choice_api_client.api_url
        logger.info(f"{request_id}_Layout Choice API URL: {api_url}")
        
        layout_result = None
        try:
            layout_result = self.layout_choice_api_client.detect(image_bytes)
            
            # 记录 API 返回结果
            if layout_result:
                boxes_data = []
                for box in layout_result.boxes:
                    boxes_data.append({
                        "cls_id": box.cls_id,
                        "coordinate": box.coordinate,
                        "label": box.label
                    })
                result_summary = {
                    "api_url": api_url,
                    "num_boxes": len(layout_result.boxes),
                    "boxes": boxes_data
                }
                logger.info(f"{request_id}_Layout Choice API 返回结果: {json.dumps(result_summary, ensure_ascii=False, indent=2)}")
            else:
                logger.warning(f"{request_id}_Layout Choice API 返回结果: None")
                
        except Exception as e:
            logger.error(f"{request_id}_Layout Choice API 调用失败: {e}")
            raise ValueError(f"Layout API 调用失败: {e}")

        if not layout_result or not getattr(layout_result, "boxes", None):
            logger.warning(f"{request_id}_Layout Choice API 未检测到任何框")
            if self.debug:
                print("[DEBUG] Layout API 未检测到任何框")
            return []

        # 优化labels提取与去重
        labels = [
            getattr(box, "label", getattr(box, "class_name", None))
            for box in layout_result.boxes
        ]
        # 去重并保留顺序
        unique_labels = []
        seen = set()
        for label in labels:
            if label not in seen:
                unique_labels.append(label)
                seen.add(label)
        
        logger.info(f"{request_id}_Layout Choice 识别结果（去重后）: {unique_labels}")
        return unique_labels
    
    def inference(self, image: np.ndarray, inference_params: Dict[str, Any]) -> dict:
        """
        主要推理过程
        
        Args:
            image: 输入图像
            inference_params: 推理参数，包含 question_info 和 question_params
            
        Returns:
            包含检测框和识别结果的字典
        """
        if self.debug:
            print(f"[DEBUG] 开始推理过程...")
            print(f"[DEBUG] 图像尺寸: {image.shape}")
        
        # 1. 图像预处理
        processed_image = self.preprocess(image)
        if processed_image is None:
            processed_image = image
        
        # Debug: 保存预处理后的图像
        if self.debug:
            preprocessed_path = self.debug_dir / "00_preprocessed_image.jpg"
            cv2.imwrite(str(preprocessed_path), processed_image)
            print(f"[DEBUG] 已保存预处理图像: {preprocessed_path}")
        
        # 2. 调用 layout 类，得到多个检测框
        detection_boxes = self.get_detection_boxes(processed_image)
        
        if self.debug:
            print(f"[DEBUG] 检测到 {len(detection_boxes)} 个填空区域")
        
        # 3. 对每个检测框进行阈值处理（可选）
        # 这里可以根据需要决定是否对每个 ROI 进行阈值处理
        
        # 4. 调用识别类进行 OCR 识别
        recognition_results = self.recognize(processed_image, detection_boxes, inference_params)
        
        if self.debug:
            print(f"[DEBUG] OCR识别完成，结果: {recognition_results}")
        
        # 5. 返回结果
        result = {
            'boxes': detection_boxes,
            'texts': recognition_results,
            'num_detections': len(detection_boxes)
        }
        
        # Debug: 保存最终结果摘要
        if self.debug:
            import json
            summary = {
                "num_detections": len(detection_boxes),
                "boxes": detection_boxes,
                "recognized_texts": recognition_results,
                "expected_answers": inference_params.get('question_info', {}).get('es_answers', []),
                "debug_dir": str(self.debug_dir)
            }
            summary_path = self.debug_dir / "08_summary.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(f"[DEBUG] 已保存结果摘要: {summary_path}")
            print(f"[DEBUG] 所有调试文件已保存到: {self.debug_dir}")
        
        return result
    
    def process(self, image_path: str, inference_params: Dict[str, Any]) -> dict:
        """
        完整的处理流程（从文件路径到结果）
        
        Args:
            image_path: 图像文件路径
            inference_params: 推理参数，包含 question_info 和 question_params
            
        Returns:
            处理结果字典
        """
        # 读取图像
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Failed to load image from {image_path}")
        
        # 执行推理
        result = self.inference(image, inference_params)
        
        # Debug: 在原始图片位置也保存一份带检测框的图像和裁剪的小图
        if self.debug and result.get('boxes'):
            # 获取原始图片目录和文件名
            original_path = Path(image_path)
            original_dir = original_path.parent
            stem = original_path.stem
            suffix = original_path.suffix
            
            # 1. 保存带检测框的图像
            output_path = original_dir / f"{stem}_with_boxes{suffix}"
            
            # 绘制检测框
            boxes = result.get('boxes', [])
            texts = result.get('texts', [])
            
            # 创建标签和颜色
            labels = []
            colors = []
            es_answers = inference_params.get('question_info', {}).get('es_answers', [])
            
            for i, box in enumerate(boxes):
                text = texts[i] if i < len(texts) else ""
                label = f"#{i+1}: {text}"
                
                # 如果有标准答案，显示匹配状态
                if i < len(es_answers):
                    expected = es_answers[i]
                    match = text.strip() == expected.strip() if text else False
                    label += f" (期望: {expected})"
                    label += " ✓" if match else " ✗"
                    colors.append((0, 255, 0) if match else (0, 0, 255))
                else:
                    colors.append((0, 255, 0))  # 默认绿色
                
                labels.append(label)
            
            # 绘制并保存
            annotated_image = self._draw_boxes_on_image(image, boxes, labels=labels, colors=colors)
            cv2.imwrite(str(output_path), annotated_image)
            print(f"[DEBUG] 已在原始图片位置保存带检测框的图像: {output_path}")
            
            # 2. 保存每个 OCR 裁剪的小图到 temp_images 目录
            cropped_dir = original_dir / f"{stem}_ocr_cropped"
            cropped_dir.mkdir(exist_ok=True)
            
            for i, (x1, y1, x2, y2) in enumerate(boxes):
                # 裁剪图像
                roi = image[y1:y2, x1:x2]
                # 保存裁剪图像
                cropped_path = cropped_dir / f"ocr_box_{i+1:02d}_({x1},{y1},{x2},{y2}).jpg"
                cv2.imwrite(str(cropped_path), roi)
            
            print(f"[DEBUG] 已在原始图片位置保存 {len(boxes)} 个OCR裁剪图像到: {cropped_dir}")
        
        return result
