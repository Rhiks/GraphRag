"""
OCR 客户端模块
提供纯数字 OCR 和全能 OCR 两种识别服务
"""

import io
import base64
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LocalPaddleOcrResult:
    """纯数字 OCR 识别结果"""
    text: str
    score: float


@dataclass
class OcrBlanksRecogResult:
    """全能 OCR 识别结果"""
    code: int
    msg: str
    latex_string: str


class LocalPaddleOcrClient:
    """
    纯数字 OCR 客户端
    用于识别纯数字内容（正数、小数、负数）
    """
    
    def __init__(self, api_url: str, timeout: int = 30):
        """
        初始化纯数字 OCR 客户端
        
        Args:
            api_url: OCR API 的 URL
            timeout: 请求超时时间（秒），默认 30
        """
        self.api_url = api_url
        self.timeout = timeout
    
    def recognize(self, image_data: bytes) -> LocalPaddleOcrResult:
        """
        识别纯数字图像
        
        Args:
            image_data: 图像的字节数据
            
        Returns:
            LocalPaddleOcrResult 对象
            
        Raises:
            requests.RequestException: 当 API 请求失败时
            ValueError: 当 API 返回数据格式错误时
        """
        # 准备 multipart/form-data 请求
        files = {
            'file': ('uploaded_file.jpg', io.BytesIO(image_data), 'image/jpeg')
        }
        
        try:
            # 发送 POST 请求
            response = requests.post(
                self.api_url,
                files=files,
                timeout=self.timeout
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result_data = response.json()
            
            # 提取文本和分数
            text = result_data.get('text', '')
            score = float(result_data.get('score', 0.0))
            
            return LocalPaddleOcrResult(text=text, score=score)
            
        except requests.RequestException as e:
            raise requests.RequestException(f"纯数字 OCR API 请求失败: {str(e)}")
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"纯数字 OCR API 返回数据格式错误: {str(e)}")


class OcrBlanksRecogClient:
    """
    全能 OCR 客户端
    用于识别非数字内容（公式、文字等）
    """
    
    def __init__(self, api_url: str, timeout: int = 30):
        """
        初始化全能 OCR 客户端
        
        Args:
            api_url: OCR API 的 URL
            timeout: 请求超时时间（秒），默认 30
        """
        self.api_url = api_url
        self.timeout = timeout
    
    def recognize(self, 
                  image_data: bytes, 
                  answer: str,
                  question_params: Dict[str, Any],
                  child_index: int = 0) -> OcrBlanksRecogResult:
        """
        识别非数字图像
        
        Args:
            image_data: 图像的字节数据
            answer: 对应的标准答案
            question_params: 题目参数
            child_index: 填空序号
            
        Returns:
            OcrBlanksRecogResult 对象
            
        Raises:
            requests.RequestException: 当 API 请求失败时
            ValueError: 当 API 返回数据格式错误时
        """
        # 将图像编码为 base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # 构建请求数据
        request_data = {
            'image': image_base64,
            'answer': answer,
            'question_params': {
                'topicId': question_params.get('topic_id', 0),
                'studentUserId': question_params.get('student_user_id', 0),
                'lessonId': 0,
                'questionId': question_params.get('question_id', 0),
                'child_index': child_index,
                'institutionId': 0
            }
        }
        
        try:
            # 发送 POST 请求
            response = requests.post(
                self.api_url,
                json=request_data,
                timeout=self.timeout
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result_data = response.json()
            
            # 提取结果
            code = result_data.get('Code', 500)
            msg = result_data.get('Msg', 'Unknown error')
            reg_results = result_data.get('reg_results', {})
            latex_string = reg_results.get('latex_string', '')
            
            return OcrBlanksRecogResult(
                code=code,
                msg=msg,
                latex_string=latex_string
            )
            
        except requests.RequestException as e:
            raise requests.RequestException(f"全能 OCR API 请求失败: {str(e)}")
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"全能 OCR API 返回数据格式错误: {str(e)}")


def is_finite_number(answer: str) -> bool:
    """
    判断答案是否为有限数字（纯数字）
    
    识别规则：
    - 纯数字：'123', '45.67', '-89', '0.5', '-12.34'
    - 非纯数字：包含字母、公式符号等
    
    Args:
        answer: 标准答案字符串
        
    Returns:
        True 表示纯数字，False 表示非纯数字
    """
    if not answer or not isinstance(answer, str):
        return False
    
    # 去除首尾空白
    answer = answer.strip()
    
    if not answer:
        return False
    
    # 去除常见的 HTML 实体和空格符号
    answer = answer.replace('&nbsp;', '').replace(' ', '').strip()
    
    if not answer:
        return False
    
    # 检查是否包含非数字字符（排除：数字、小数点、负号）
    # 如果包含其他字符（字母、括号、斜杠等），则不是纯数字
    allowed_chars = set('0123456789.-')
    
    # 如果有任何字符不在允许的字符集中，则不是纯数字
    if not all(c in allowed_chars for c in answer):
        return False
    
    # 尝试将其转换为浮点数
    try:
        float(answer)
        return True
    except ValueError:
        return False
