import cv2
import requests
import numpy as np
import sys
import os
from pathlib import Path

# 添加项目根到路径，以 main._traCV 包形式导入，避免相对导入及 ..config 错误
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from main._traCV.traditional_cv import TraditionalCV

def download_image(img_url: str, save_path: str = None) -> str:
    """
    下载图片到本地（如果已存在则跳过下载）
    
    Args:
        img_url: 图片URL
        save_path: 保存路径，如果为None则自动生成
        
    Returns:
        本地图片路径
    """
    if save_path is None:
        # 从URL提取文件名
        filename = img_url.split('/')[-1]
        # 如果文件名包含查询参数，只取第一部分
        if '?' in filename:
            filename = filename.split('?')[0]
        save_path = str(Path(__file__).parent / "temp_images" / filename)
    
    # 创建目录
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # 如果图片已存在，直接返回
    if os.path.exists(save_path):
        print(f"图片已存在，跳过下载: {save_path}")
        return save_path
    
    # 下载图片
    print(f"正在下载图片: {img_url}")
    response = requests.get(img_url, timeout=30)
    response.raise_for_status()
    
    # 保存图片
    with open(save_path, 'wb') as f:
        f.write(response.content)
    
    print(f"图片已保存到: {save_path}")
    return save_path

def test_recognize_choice():
    #img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1770016407444_78_8769308.1770016407436.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1770276756673_54_1604961.1770276756667.jpg"
    img_url = "https://aixuexi-jzx-file.oss-cn-beijing.aliyuncs.com/jzxfile/1768976166417_5_9668168.1768976166412.jpg"
    
    # 1. 先下载图片到本地
    local_image_path = download_image(img_url)
    
    # 2. 从本地文件读取图片
    image = cv2.imread(local_image_path)
    if image is None:
        raise ValueError(f"无法读取图片文件: {local_image_path}")
    
    print(f"图片尺寸: {image.shape}")
    
    # 3. 根据你的实际配置传递参数
    traditional_cv = TraditionalCV(
        layout_api_url="http://localhost:8501/layout", 
        local_paddle_ocr_url=None,
        ocr_blanks_recog_url=None,
        Layout_choice_api_url="https://cv.dev.aixuexi.com/layout/choice/predict",
        debug=True,
        debug_dir="./debug"
    )

    # 4. 调用 recognize_choice（现在它接受 np.ndarray）
    results = traditional_cv.recognize_choice(image)
    print("recognize_choice results:", results)

if __name__ == "__main__":
    print("test_recognize_choice")
    test_recognize_choice()
