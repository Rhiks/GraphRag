#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
脚本功能：
1. 读取 evals/results_500concurrent/test_infer_results_20260105_dev.jsonl
2. 找到包含 "cv_recall" 的行，提取对应的 image_url
3. 从 objective-wide-table-sample-20260105.jsonl 中找到对应的 image_url 的行
4. 将这些行复制到新文件 cv_recall_in500.jsonl
"""

import json
import os
from pathlib import Path

def extract_cv_recall():
    # 文件路径（相对于脚本所在目录的上级目录）
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if 'main' in base_dir:
        base_dir = os.path.dirname(base_dir)  # 回到 llm_blanks_recog_ocr 目录
    
    input_file = os.path.join(base_dir, "results_500concurrent/test_infer_results_20260105_dev.jsonl")
    source_file = os.path.join(base_dir, "objective-wide-table-sample-20260105.jsonl")
    output_file = os.path.join(base_dir, "cv_recall_in500.jsonl")
    
    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误：文件 {input_file} 不存在")
        return
    
    if not os.path.exists(source_file):
        print(f"错误：文件 {source_file} 不存在")
        return
    
    # 第一步：读取 test_infer_results_20260105_dev.jsonl，找到包含 cv_recall 的行
    print(f"正在读取 {input_file}...")
    image_urls_with_cv_recall = set()
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                # 检查是否包含 cv_recall 字段（可能在嵌套结构中）
                # 路径：infer_results.recog_results.cv_middle_results.cv_recall
                cv_recall = None
                if 'infer_results' in data:
                    infer_results = data.get('infer_results', {})
                    recog_results = infer_results.get('recog_results', {})
                    cv_middle_results = recog_results.get('cv_middle_results', {})
                    cv_recall = cv_middle_results.get('cv_recall')
                
                if cv_recall is not None  and cv_recall==1:
                    # 提取 image_url（可能在 question_info.img_url 中）
                    image_url = None
                    if 'question_info' in data:
                        question_info = data.get('question_info', {})
                        img_urls = question_info.get('img_url', [])
                        if img_urls and isinstance(img_urls, list) and len(img_urls) > 0:
                            image_url = img_urls[0]
                    
                    if image_url:
                        image_urls_with_cv_recall.add(image_url)
                        print(f"找到包含 cv_recall={cv_recall} 的记录 (行 {line_num}): {image_url}")
            except json.JSONDecodeError as e:
                print(f"警告：第 {line_num} 行 JSON 解析失败: {e}")
                continue
    
    print(f"\n共找到 {len(image_urls_with_cv_recall)} 个包含 cv_recall 的 image_url")
    
    if not image_urls_with_cv_recall:
        print("没有找到包含 cv_recall 的记录，退出")
        return
    
    # 第二步：从 objective-wide-table-sample-20260105.jsonl 中找到对应的行
    print(f"\n正在读取 {source_file}...")
    matched_lines = []
    
    with open(source_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                # 提取 image_url（可能在 question_info.img_url 数组中）
                image_url = None
                if 'question_info' in data:
                    question_info = data.get('question_info', {})
                    img_urls = question_info.get('img_url', [])
                    if img_urls and isinstance(img_urls, list) and len(img_urls) > 0:
                        image_url = img_urls[0]
                
                # 如果这个 image_url 在我们要找的集合中，保存这一行
                if image_url and image_url in image_urls_with_cv_recall:
                    matched_lines.append(line)
                    if len(matched_lines) <= 10 or len(matched_lines) % 50 == 0:
                        print(f"找到匹配记录 (行 {line_num}): {image_url}")
            except json.JSONDecodeError as e:
                print(f"警告：第 {line_num} 行 JSON 解析失败: {e}")
                continue
    
    print(f"\n共找到 {len(matched_lines)} 条匹配的记录")
    
    # 第三步：写入新文件
    if matched_lines:
        print(f"\n正在写入 {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in matched_lines:
                f.write(line + '\n')
        print(f"成功！已将 {len(matched_lines)} 条记录写入 {output_file}")
    else:
        print("没有找到匹配的记录，未创建输出文件")

if __name__ == "__main__":
    extract_cv_recall()
