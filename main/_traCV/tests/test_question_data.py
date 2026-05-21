#!/usr/bin/env python3
"""
基于 question_data.json 测试 TraditionalCV 的完整流程
"""

import sys
import json
import os
from pathlib import Path
import cv2
import numpy as np
import requests
from typing import Dict, Any, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from main._traCV.traditional_cv import TraditionalCV


def load_question_data(json_path: str) -> Dict[str, Any]:
    """加载测试数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def download_image(img_url: str, save_path: Optional[str] = None) -> str:
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


def build_inference_params(question_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 question_data.json 构建 inference_params
    
    Args:
        question_data: question_data.json 的内容
        
    Returns:
        inference_params 字典
    """
    question_info = question_data.get("question_info", {})
    topic_info = question_info.get("topic_info", {})
    user_info = question_data.get("user_info", {})
    
    # 提取标准答案
    answers = topic_info.get("answers", [])
    es_answers = []
    for ans in answers:
        if isinstance(ans, dict):
            text = ans.get("text", "")
            if text:
                es_answers.append(text)
        elif isinstance(ans, str):
            es_answers.append(ans)
    
    # 提取题目文本
    stem_obj = topic_info.get("stem", {})
    if isinstance(stem_obj, dict):
        stem = stem_obj.get("text", "")
    else:
        stem = str(stem_obj)
    
    # 构建 question_info
    question_info_dict = {
        "es_answers": es_answers,
        "stem": stem
    }
    
    # 构建 question_params
    student_user_id = user_info.get("student_user_id")
    topic_id = topic_info.get("topic_id")
    topic_type = topic_info.get("topic_type")
    question_id = question_info.get("question_id")
    
    question_params = {
        "student_user_id": student_user_id,
        "topic_id": topic_id,
        "topic_type": topic_type,
    }
    
    if question_id is not None:
        question_params["question_id"] = question_id
    else:
        question_params["question_id"] = -1
    
    # 默认 page_source
    question_params["page_source"] = 0
    
    # 构建 inference_params
    inference_params = {
        "question_info": question_info_dict,
        "question_params": question_params,
    }
    
    return inference_params


def test_traditional_cv_with_question_data():
    """使用 question_data.json 测试 TraditionalCV"""
    print("=" * 70)
    print("基于 question_data.json 测试 TraditionalCV")
    print("=" * 70)
    
    # 1. 加载测试数据
    json_path = Path(__file__).parent / "question_data.json"
    print(f"\n1. 加载测试数据: {json_path}")
    question_data = load_question_data(str(json_path))
    print(f"   ✅ 测试数据加载成功")
    
    # 2. 提取图片URL
    question_info = question_data.get("question_info", {})
    img_urls = question_info.get("img_url", [])
    if not img_urls:
        print("   ❌ 未找到图片URL")
        return False
    
    img_url = img_urls[0]
    print(f"   图片URL: {img_url}")
    
    # 3. 下载图片
    print(f"\n2. 下载图片")
    try:
        image_path = download_image(img_url)
        print(f"   ✅ 图片下载成功")
    except Exception as e:
        print(f"   ❌ 图片下载失败: {e}")
        return False
    
    # 4. 构建 inference_params
    print(f"\n3. 构建 inference_params")
    inference_params = build_inference_params(question_data)
    print(f"   question_info: {inference_params['question_info']}")
    print(f"   question_params: {inference_params['question_params']}")
    print(f"   ✅ inference_params 构建成功")
    
    # 5. 初始化 TraditionalCV
    print(f"\n4. 初始化 TraditionalCV")
    try:
        # 检查是否启用debug模式（通过环境变量或命令行参数）
        # 默认启用 debug 模式，可以通过 --no-debug 或 DEBUG=false 关闭
        import sys
        debug_mode = True  # 默认启用
        if "--no-debug" in sys.argv:
            debug_mode = False
        elif os.getenv("DEBUG", "").lower() == "false":
            debug_mode = False
        elif os.getenv("DEBUG", "").lower() == "true":
            debug_mode = True
        
        debug_dir = os.getenv("DEBUG_DIR", None)
        
        if debug_mode:
            print(f"   🔍 Debug 模式已启用")
            if debug_dir:
                print(f"   📁 Debug 输出目录: {debug_dir}")
        else:
            print(f"   ⚙️  Debug 模式已关闭（使用 --no-debug 或 DEBUG=false 关闭）")
        
        # 从配置文件读取API URL（如果配置了的话）
        cv_processor = TraditionalCV(debug=debug_mode, debug_dir=debug_dir)
        print(f"   ✅ TraditionalCV 初始化成功")
    except Exception as e:
        print(f"   ❌ TraditionalCV 初始化失败: {e}")
        print(f"   提示: 请确保配置文件中设置了相应的 API URL")
        return False
    
    # 6. 执行推理
    print(f"\n5. 执行推理")
    try:
        result = cv_processor.process(image_path, inference_params)
        print(f"   ✅ 推理完成")
        print(f"\n   推理结果:")
        print(f"   - 检测框数量: {result.get('num_detections', 0)}")
        print(f"   - 检测框: {result.get('boxes', [])}")
        print(f"   - 识别文本: {result.get('texts', [])}")
        
        # 7. 与标准答案对比
        print(f"\n6. 结果对比")
        gt_data = question_data.get("gt", {})
        gt_ocr_results = gt_data.get("ocr_results", [])
        is_correct = gt_data.get("is_correct", False)
        
        print(f"   标准答案: {gt_ocr_results}")
        print(f"   识别结果: {result.get('texts', [])}")
        print(f"   是否正确: {is_correct}")
        
        # 详细对比
        recognized_texts = result.get('texts', [])
        if recognized_texts:
            print(f"\n   详细对比:")
            for i, recognized in enumerate(recognized_texts):
                if i < len(gt_ocr_results):
                    gt_answer = gt_ocr_results[i]
                    match = recognized.strip() == gt_answer.strip()
                    status = "✅" if match else "❌"
                    print(f"      [{i+1}] {status} 识别: '{recognized}' | 标准: '{gt_answer}'")
                else:
                    print(f"      [{i+1}] ⚠️  识别: '{recognized}' | 标准: (无)")
            
            # 检查是否所有结果都匹配
            all_match = len(recognized_texts) == len(gt_ocr_results) and all(
                rec.strip() == gt.strip() 
                for rec, gt in zip(recognized_texts, gt_ocr_results)
            )
            if all_match:
                print(f"\n   ✅ 所有识别结果都匹配标准答案")
            else:
                print(f"\n   ⚠️  部分识别结果与标准答案不匹配")
        else:
            print(f"   ⚠️  未识别到任何文本")
        
        # 8. 输出最终结果摘要
        print(f"\n7. 最终结果摘要")
        print(f"   {'-' * 60}")
        print(f"   检测框数量: {result.get('num_detections', 0)}")
        print(f"   识别文本: {result.get('texts', [])}")
        print(f"   标准答案: {gt_ocr_results}")
        
        # 计算匹配结果
        if recognized_texts and gt_ocr_results:
            all_match = (len(recognized_texts) == len(gt_ocr_results) and 
                        all(rec.strip() == gt.strip() 
                            for rec, gt in zip(recognized_texts, gt_ocr_results)))
            match_status = "是" if all_match else "否"
        else:
            match_status = "否（缺少识别结果或标准答案）"
        
        print(f"   结果匹配: {match_status}")
        print(f"   {'-' * 60}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 推理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    try:
        # 显示使用说明
        import sys
        if "--help" in sys.argv or "-h" in sys.argv:
            print("=" * 70)
            print("使用说明:")
            print("=" * 70)
            print("默认模式（Debug 模式已启用，会保存中间结果和可视化）:")
            print("  python test_question_data.py")
            print("")
            print("关闭 Debug 模式:")
            print("  python test_question_data.py --no-debug")
            print("  或")
            print("  DEBUG=false python test_question_data.py")
            print("")
            print("指定 Debug 输出目录:")
            print("  DEBUG_DIR=/path/to/debug python test_question_data.py")
            print("=" * 70)
            return 0
        
        success = test_traditional_cv_with_question_data()
        
        print("\n" + "=" * 70)
        if success:
            print("✅ 测试完成")
            # 如果启用了debug模式，显示输出目录
            import sys
            debug_enabled = True
            if "--no-debug" in sys.argv or os.getenv("DEBUG", "").lower() == "false":
                debug_enabled = False
            
            if debug_enabled:
                debug_dir = os.getenv("DEBUG_DIR", None)
                if debug_dir:
                    print(f"📁 Debug 文件保存在: {debug_dir}")
                else:
                    project_root = Path(__file__).parent.parent.parent.parent
                    print(f"📁 Debug 文件保存在: {project_root}/debug_output/")
        else:
            print("❌ 测试失败")
        print("=" * 70)
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
