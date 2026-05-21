"""
Layout API 客户端
负责调用 REST API 获取填空区域检测结果
"""

import io
from typing import List, Dict, Any, Optional
import requests
from dataclasses import dataclass


@dataclass
class Box:
    """检测框数据类"""
    cls_id: int
    coordinate: List[int]  # [x1, y1, x2, y2]
    label: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Box':
        """从字典创建 Box 对象"""
        # 处理坐标，确保是整数
        raw_coordinate = data.get('coordinate', [])
        coordinate = []
        for val in raw_coordinate:
            try:
                # 将字符串或浮点数转换为整数
                coordinate.append(int(round(float(val))))
            except (ValueError, TypeError):
                coordinate.append(0)
        
        return cls(
            cls_id=data.get('cls_id', 0),
            coordinate=coordinate,
            label=data.get('label', '')
        )


@dataclass
class LayoutResult:
    """Layout 检测结果"""
    boxes: List[Box]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutResult':
        """从字典创建 LayoutResult 对象"""
        boxes_data = data.get('data', {}).get('boxes', [])
        boxes = [Box.from_dict(box_data) for box_data in boxes_data]
        return cls(boxes=boxes)


class LayoutAPIClient:
    """Layout API 客户端"""

    def __init__(self, api_url: str, threshold: float = 0.3, timeout: int = 30):
        """
        初始化 Layout API 客户端

        Args:
            api_url: Layout API 的 URL
            threshold: 检测阈值，默认 0.3
            timeout: 请求超时时间（秒），默认 30
        """
        self.api_url = api_url
        self.threshold = threshold
        self.timeout = timeout

    def detect(self, image_data: bytes) -> Optional[LayoutResult]:
        """
        调用 Layout API 进行检测

        Args:
            image_data: 图像的字节数据

        Returns:
            LayoutResult 对象，包含检测到的所有框；失败返回 None
        
        Raises:
            requests.RequestException: 当 API 请求失败时
            ValueError: 当 API 返回数据格式错误时
        """
        # 检测 MIME 类型
        mime_type = self._detect_mime_type(image_data)
        
        # 生成文件名
        filename = self._generate_filename(mime_type)
        
        # 准备 multipart/form-data 请求
        files = {
            'file': (filename, io.BytesIO(image_data), mime_type)
        }
        
        data = {
            'threshold': self.threshold
        }
        
        try:
            # 发送 POST 请求
            response = requests.post(
                self.api_url,
                files=files,
                data=data,
                timeout=self.timeout
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应
            result_data = response.json()
            layout_result = LayoutResult.from_dict(result_data)
            
            return layout_result
            
        except requests.RequestException as e:
            raise requests.RequestException(f"Layout API 请求失败: {str(e)}")
        except (KeyError, ValueError) as e:
            raise ValueError(f"Layout API 返回数据格式错误: {str(e)}")

    @staticmethod
    def _detect_mime_type(image_data: bytes) -> str:
        """
        检测图像的 MIME 类型

        Args:
            image_data: 图像字节数据

        Returns:
            MIME 类型字符串
        """
        # 简单的文件头检测
        if image_data.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        elif image_data.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        elif image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a'):
            return 'image/gif'
        elif image_data.startswith(b'BM'):
            return 'image/bmp'
        elif image_data.startswith(b'RIFF') and b'WEBP' in image_data[:20]:
            return 'image/webp'
        else:
            return 'application/octet-stream'

    @staticmethod
    def _generate_filename(mime_type: str) -> str:
        """
        根据 MIME 类型生成文件名

        Args:
            mime_type: MIME 类型

        Returns:
            文件名
        """
        extension_map = {
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/bmp': 'bmp',
            'image/webp': 'webp',
            'application/pdf': 'pdf',
            'image/tiff': 'tiff'
        }
        
        ext = extension_map.get(mime_type, '')
        if ext:
            return f'uploaded_file.{ext}'
        return 'uploaded_file'
