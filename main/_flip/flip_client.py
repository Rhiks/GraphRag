"""
Flip OCR 服务客户端
读取图片，转换为base64发送请求，并保存输出的final图片
"""
import os
import argparse
import requests
import cv2
from typing import Optional
import time
import numpy as np
import pdb
import os, sys
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError


def base64_to_bgr_image(base64_str: str) -> Optional[np.ndarray]:
    """
    将base64编码的字符串转换为BGR格式的numpy数组图像
    
    Args:
        base64_str: base64编码的图片字符串，可以包含data URL前缀
        
    Returns:
        BGR格式的numpy数组图像，如果解码失败返回None
    """
    try:
        # 移除可能的data URL前缀（如 "data:image/jpeg;base64,"）
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        
        # 解码base64
        image_bytes = base64.b64decode(base64_str)
        
        # 将字节转换为numpy数组
        nparr = np.frombuffer(image_bytes, np.uint8)
        
        # 解码图片（BGR格式）
        bgr_im = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return bgr_im
    except Exception as e:
        print(f"Base64转BGR图像失败: {str(e)}")
        return None


def bgr_image_to_base64(bgr_im: np.ndarray, format: str = '.jpg', quality: int = 95) -> Optional[str]:
    """
    将BGR格式的numpy数组图像转换为base64编码的字符串
    
    Args:
        bgr_im: BGR格式的numpy数组图像
        format: 图片格式，如 '.jpg', '.png' 等
        quality: JPEG质量（仅对JPEG格式有效，1-100）
        
    Returns:
        base64编码的图片字符串，如果编码失败返回None
    """
    try:
        if bgr_im is None or not isinstance(bgr_im, np.ndarray):
            return None
        
        # 设置编码参数
        encode_params = []
        if format.lower() == '.jpg' or format.lower() == '.jpeg':
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        elif format.lower() == '.png':
            encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 9]
        
        # 将BGR图片编码
        success, encoded_img = cv2.imencode(format, bgr_im, encode_params)
        
        if success:
            # 转换为base64字符串
            base64_str = base64.b64encode(encoded_img.tobytes()).decode('utf-8')
            return base64_str
        else:
            print("图片编码失败")
            return None
    except Exception as e:
        print(f"BGR图像转Base64失败: {str(e)}")
        return None


def image_path_to_base64(image_path: str) -> Optional[str]:
    """
    读取图片文件并转换为base64字符串
    
    Args:
        image_path: 图片文件路径
        
    Returns:
        base64编码的图片字符串，如果失败返回None
    """
    try:
        # 读取图片为BGR格式
        bgr_im = cv2.imread(image_path)
        if bgr_im is None:
            print(f"错误: 无法读取图片 {image_path}")
            return None
        
        # 转换为base64
        base64_str = bgr_image_to_base64(bgr_im)
        return base64_str
    except Exception as e:
        print(f"转换图片为base64失败: {str(e)}")
        return None


def save_base64_image(base64_str: str, output_path: str) -> bool:
    """
    将base64字符串保存为图片文件
    
    Args:
        base64_str: base64编码的图片字符串
        output_path: 输出图片路径
        
    Returns:
        是否保存成功
    """
    try:
        if base64_str is None:
            print("错误: base64字符串为空")
            return False
        
        # 转换为BGR图像
        bgr_im = base64_to_bgr_image(base64_str)
        if bgr_im is None:
            print("错误: 无法解码base64图片")
            return False
        
        # 保存图片
        success = cv2.imwrite(output_path, bgr_im)
        if success:
            return True
        else:
            print(f"错误: 保存图片失败 {output_path}")
            return False
    except Exception as e:
        print(f"保存图片失败: {str(e)}")
        return False


def send_request(server_url: str, bgr_im: np.ndarray) -> tuple[Optional[dict], Optional[float]]:
    """
    发送推理请求到服务器（使用BGR图像）
    
    Args:
        server_url: 服务器URL（如 http://localhost:8000）
        bgr_im: BGR格式的numpy数组图像
        
    Returns:
        元组 (服务器响应的JSON数据, 请求耗时(秒))，如果失败返回 (None, None) 或 (None, 耗时)
    """
    try:
        # 检查输入图像是否有效
        if bgr_im is None or not isinstance(bgr_im, np.ndarray):
            print(f"错误: 输入的BGR图像无效")
            return None, None
        
        # 转换为base64
        base64_str = bgr_image_to_base64(bgr_im)
        if base64_str is None:
            return None, None
        
        # 准备请求数据
        data = {"image": base64_str}
        
        # 发送POST请求
        api_url = f"{server_url}/inference_base64"
        try:
            t0 = time.time()
            response = requests.post(api_url, json=data, timeout=.3)
            t1 = time.time()
            duration = t1 - t0
        except Exception as e:
            return None, None
        
        # 检查响应状态
        if response.status_code != 200:
            print(f"错误: 服务器返回状态码 {response.status_code}")
            print(f"错误信息: {response.text}")
            print(f"请求耗时: {np.round(duration, 4)}s")
            return None, duration
        
        # 解析响应
        result = response.json()
        print(f"请求耗时: {np.round(duration, 4)}s")
        
        return result, duration
        
    except requests.exceptions.Timeout:
        print("错误: 请求超时")
        return None, None
    except requests.exceptions.ConnectionError:
        print(f"错误: 无法连接到服务器 {server_url}")
        return None, None
    except Exception as e:
        print(f"错误: 处理请求时发生异常: {str(e)}")
        return None, None


def send_request_bgrim(server_url: str, bgr_im: np.ndarray) -> tuple[Optional[dict], Optional[np.ndarray], Optional[float]]:
    """
    发送推理请求到服务器（使用BGR图像），并返回final_res_image
    使用ThreadPoolExecutor严格控制请求时长不超过500ms
    
    Args:
        server_url: 服务器URL（如 http://localhost:8000）
        bgr_im: BGR格式的numpy数组图像
        
    Returns:
        元组 (服务器响应的JSON数据, final_res_image(BGR格式), 请求耗时(秒))
        如果失败返回 (None, None, None) 或 (None, None, 耗时)
        如果成功但没有final_res_image，返回 (result, None, duration)
    """
    try:
        # 检查输入图像是否有效
        if bgr_im is None or not isinstance(bgr_im, np.ndarray):
            print(f"错误: 输入的BGR图像无效")
            return None, None, None
        
        # 转换为base64
        base64_str = bgr_image_to_base64(bgr_im)
        if base64_str is None:
            return None, None, None
        
        # 准备请求数据
        data = {"image": base64_str}
        api_url = f"{server_url}/inference_base64"
        
        # 定义内部请求函数
        def _make_request():
            """内部函数：执行实际的HTTP请求"""
            t0 = time.time()
            response = requests.post(api_url, json=data, timeout=0.5)
            t1 = time.time()
            duration = t1 - t0
            return response, duration
        
        # 使用ThreadPoolExecutor严格控制总时长不超过500ms
        t_start = time.time()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_make_request)
            try:
                # 严格控制总时长不超过500ms
                response, duration = future.result(timeout=0.5)
                t_end = time.time()
                total_duration = t_end - t_start
            except TimeoutError:
                # 超时，取消任务
                future.cancel()
                print("错误: 请求超时（超过500ms）")
                return None, None, None
            except Exception as e:
                print(f"错误: 请求执行异常: {str(e)}")
                return None, None, None
        
        # 检查响应状态
        if response.status_code != 200:
            print(f"错误: 服务器返回状态码 {response.status_code}")
            print(f"错误信息: {response.text}")
            print(f"请求耗时: {np.round(total_duration, 4)}s")
            return None, None, total_duration
        
        # 解析响应
        result = response.json()
        print(f"请求耗时: {np.round(total_duration, 4)}s")
        #pdb.set_trace()
        
        # 提取final_res_image（如果存在）
        #pdb.set_trace()
        final_res_image = None
        if isinstance(result, dict):
            if 'final_choice' in result and result['final_choice']=="raw":
                final_res_image = bgr_im
            elif 'final_im_base64' in result:
                final_im_base64 = result['final_im_base64']
                final_res_image = base64_to_bgr_image(final_im_base64)
            
                if final_res_image is None:
                    print("警告: 无法解码final_res_image")
        
        return result, final_res_image, total_duration
        
    except requests.exceptions.Timeout:
        print("错误: 请求超时")
        return None, None, None
    except requests.exceptions.ConnectionError:
        print(f"错误: 无法连接到服务器 {server_url}")
        return None, None, None
    except Exception as e:
        print(f"错误: 处理请求时发生异常: {str(e)}")
        return None, None, None
def send_inference_request(server_url: str, image_path: str) -> tuple[Optional[dict], Optional[float]]:
    """
    发送推理请求到服务器
    
    Args:
        server_url: 服务器URL（如 http://localhost:8000）
        image_path: 输入图片路径
        
    Returns:
        元组 (服务器响应的JSON数据, 请求耗时(秒))，如果失败返回 (None, None) 或 (None, 耗时)
    """
    try:
        # 检查图片文件是否存在
        if not os.path.exists(image_path):
            print(f"错误: 图片文件不存在: {image_path}")
            return None, None
        
        # 转换为base64
        base64_str = image_path_to_base64(image_path)
        if base64_str is None:
            return None, None
        
        # 准备请求数据
        data = {"image": base64_str}
        
        # 发送POST请求
        api_url = f"{server_url}/inference_base64"
        t0 = time.time()
        try:
            response = requests.post(api_url, json=data, timeout=2)
            t1 = time.time()
            duration = t1 - t0
        except Exception as e:
            return None, None
        
        # 检查响应状态
        if response.status_code != 200:
            print(f"错误: 服务器返回状态码 {response.status_code}")
            print(f"错误信息: {response.text}")
            print(f"请求耗时: {np.round(duration, 4)}s")
            return None, duration
        
        # 解析响应
        result = response.json()
        print(f"请求耗时: {np.round(duration, 4)}s")
        
        return result, duration
        
    except requests.exceptions.Timeout:
        print("错误: 请求超时")
        return None, None
    except requests.exceptions.ConnectionError:
        print(f"错误: 无法连接到服务器 {server_url}")
        return None, None
    except Exception as e:
        print(f"错误: 处理请求时发生异常: {str(e)}")
        return None, None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Flip OCR 服务客户端 - 发送图片进行OCR识别并保存结果',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基本使用（自动保存到同目录）
  python flip_client.py --image path/to/image.jpg
  
  # 指定服务器地址和输出路径
  python flip_client.py --image path/to/image.jpg --server http://localhost:8000 --output result.jpg
  
  # 批量处理多个图片
  python flip_client.py --image img1.jpg img2.jpg img3.jpg
        """
    )
    
    parser.add_argument(
        '--image',
        nargs='+',
        required=True,
        help='输入图片路径（可以指定多个）'
    )
    parser.add_argument(
        '--server',
        default='http://localhost:8000',
        help='服务器地址 (默认: http://localhost:8000)'
    )
    parser.add_argument(
        '--output',
        help='输出图片路径（如果指定多个输入图片，此参数将被忽略，使用自动生成的路径）'
    )
    
    args = parser.parse_args()
    
    # 检查服务器是否可用
    try:
        health_url = f"{args.server}/health"
        print(f"检查服务器连接: {health_url}")
        response = requests.get(health_url, timeout=5)
        if response.status_code != 200:
            print(f"警告: 服务器健康检查失败，状态码: {response.status_code}")
        else:
            print("服务器连接正常")
    except Exception as e:
        print(f"警告: 无法连接到服务器 {args.server}: {str(e)}")
        print("将继续尝试发送请求...")
    
    print("\n" + "="*50)
    
    # 处理每个图片
    image_paths = args.image
    for i, image_path in enumerate(image_paths):
        print(f"\n处理图片 {i+1}/{len(image_paths)}: {image_path}")
        print("-" * 50)
        
        # 如果只有一个图片且指定了输出路径，使用指定的输出路径
        # 如果有多个图片，忽略输出路径参数，使用自动生成的路径
        output_path = args.output if len(image_paths) == 1 else None
        
        result = send_inference_request(args.server, image_path, output_path)
        
        if result is None:
            print(f"处理失败: {image_path}")
        else:
            print(f"处理成功: {image_path}")
    
    print("\n" + "="*50)
    print("所有图片处理完成")


if __name__ == "__main__":
    #main()
    server_url = "https://cv.dev.aixuexi.com/flip-images"
    image_path = "/data/weima1/flip_images_/res_jsonl_images/2_9263098_unknown.jpg"
    output_path = "./res/2.jpg"
    
    # 并发执行10个请求
    num_requests = 1
    print(f"开始并发执行 {num_requests} 个请求...")
    print("=" * 50)
    
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        # 提交所有任务
        futures = [executor.submit(send_inference_request, server_url, image_path) 
                   for _ in range(num_requests)]
        
        # 收集结果
        for i, future in enumerate(as_completed(futures), 1):
            try:
                result, request_time = future.result()
                results.append((i, result, request_time))
                #print(f"请求 {i}/{num_requests} 完成, 耗时: {request_time:.4f}s")
                print(f"请求 {i}/{num_requests} 完成, 耗时: {request_time}s")
            except Exception as e:
                print(f"请求 {i}/{num_requests} 失败: {str(e)}")
                results.append((i, None, None))
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print("\n" + "=" * 50)
    print(f"所有请求完成，总耗时: {total_time:.4f}s")
    print(f"平均每个请求耗时: {total_time/num_requests:.4f}s")
    print("\n结果汇总:")
    for i, result, request_time in results:
        if result is not None:
            print(f"请求 {i}: 成功, 耗时: {request_time:.4f}s")
        else:
            print(f"请求 {i}: 失败")

