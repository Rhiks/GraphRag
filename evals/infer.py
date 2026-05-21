#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
推理脚本：从 JSONL 文件读取测试样例，调用 /judge/objective 接口，保存推理结果
"""

import os
import sys
import json
import yaml
import logging
import requests
import time
import shutil
import argparse
import uuid
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# 获取脚本所在目录（工作区根目录）
WORKSPACE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(WORKSPACE_DIR))


# 配置日志
def setup_logging(log_level: str, log_file: str):
    """设置日志配置"""
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger(__name__)


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def convert_to_api_input(sample: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    将测试样例转换为 JudgeRequest API 输入格式（用于 /judge/objective 接口）

    Args:
        sample: 原始测试样例 JSON 对象

    Returns:
        转换后的 JudgeRequest 格式，如果转换失败返回 None
    """
    try:
        question_info = sample.get("question_info", {})
        topic_info = question_info.get("topic_info", {})
        user_info = sample.get("user_info", {})

        # 检查必填字段
        student_user_id = user_info.get("student_user_id")
        topic_id = topic_info.get("topic_id")
        topic_type = topic_info.get("topic_type")
        if student_user_id is None or topic_id is None or topic_type is None:
            return None

        # 提取图片 URL（从数组取第一个）
        img_urls = question_info.get("img_url", [])
        if not img_urls:
            return None
        img_url = img_urls[0]

        # 直接使用原始数据结构，只做必要的重组
        # topic_info 已经符合格式，直接使用
        # 只需要提取 img_url 并重组结构

        # 构建 question_info（topic_info 直接使用原始数据）
        question_info_dict = {
            "topic_info": topic_info,  # 直接使用，不需要转换
            "img_url": img_url,
        }
        question_id = question_info.get("question_id")
        if question_id is not None:
            question_info_dict["question_id"] = question_id

        # 构建完整的 JudgeRequest
        api_input = {
            "student_info": user_info,  # user_info 格式已经符合 student_info
            "question_info": question_info_dict,
            "conversation_id": str(uuid.uuid4()),  # 生成一个 conversation_id
            "page_source": sample.get("page_source", 0),  # 默认值为 0
        }

        return api_input

    except Exception as e:
        # 使用标准输出，因为此时 logger 可能还未初始化
        print(f"转换样例失败: {e}", file=sys.stderr)
        return None


def call_api(
    api_url: str,
    api_input: Dict[str, Any],
    timeout: int = 60,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    调用 API 接口

    Args:
        api_url: API 地址
        api_input: API 输入数据
        timeout: 超时时间
        headers: 请求头

    Returns:
        API 响应结果，如果失败返回 None
    """
    # 打印请求信息
    request_headers = headers or {"Content-Type": "application/json"}
    logging.info("=" * 60)
    logging.info(f"准备调用 API: {api_url}")
    logging.info(f"请求头: {json.dumps(request_headers, ensure_ascii=False, indent=2)}")
    logging.info(f"超时时间: {timeout} 秒")
    logging.info(f"请求体: {json.dumps(api_input, ensure_ascii=False, indent=2)}")
    logging.info("=" * 60)

    try:
        response = requests.post(
            api_url, json=api_input, headers=request_headers, timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logging.error(f"API 请求超时: {api_url}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API 请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"API 响应解析失败: {e}")
        return None


def call_judge_api(
    judge_url: str,
    topic_id: int,
    recog_results: Dict[str, Any],
    timeout: int = 60,
    salt: str = "llm-router",
) -> Optional[Dict[str, Any]]:
    """
    调用判题接口

    Args:
        judge_url: 判题接口地址
        topic_id: 题目ID
        recog_results: 识别结果，包含 stu_answers
        timeout: 超时时间
        salt: 请求头中的盐值

    Returns:
        判题结果，如果失败返回 None
    """
    # 构建请求体
    judge_input = {
        "topic_id": topic_id,
        "recog_results": {"stu_answers": recog_results.get("stu_answers", [])},
    }

    # 构建请求头
    headers = {"Content-Type": "application/json", "salt": salt}

    # 打印请求信息
    logging.info("=" * 60)
    logging.info(f"准备调用判题接口: {judge_url}")
    logging.info(f"请求头: {json.dumps(headers, ensure_ascii=False, indent=2)}")
    logging.info(f"超时时间: {timeout} 秒")
    logging.info(f"请求体: {json.dumps(judge_input, ensure_ascii=False, indent=2)}")
    logging.info("=" * 60)

    try:
        response = requests.post(
            judge_url, json=judge_input, headers=headers, timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logging.error(f"判题接口请求超时: {judge_url}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"判题接口请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"判题接口响应解析失败: {e}")
        return None


def call_subjective_judge_sse(
    api_url: str,
    api_input: Dict[str, Any],
    timeout: int = 60,
    headers: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    调用主观题判题 SSE 接口并解析响应

    Args:
        api_url: API 地址
        api_input: API 输入数据
        timeout: 超时时间
        headers: 请求头

    Returns:
        包含 is_correct 字段的字典，如果失败返回 None
    """
    request_headers = headers or {"Content-Type": "application/json"}
    logging.info("=" * 60)
    logging.info(f"准备调用主观题判题 SSE 接口: {api_url}")
    logging.info(f"请求头: {json.dumps(request_headers, ensure_ascii=False, indent=2)}")
    logging.info(f"超时时间: {timeout} 秒")
    logging.info(f"请求体: {json.dumps(api_input, ensure_ascii=False, indent=2)}")
    logging.info("=" * 60)

    try:
        # 调用 SSE 接口
        response = requests.post(
            api_url,
            json=api_input,
            headers=request_headers,
            timeout=timeout,
            stream=True,
        )
        response.raise_for_status()

        # 解析 SSE 响应流
        # SSE 格式: event: <event_type>\ndata: <data>\n\n
        final_response = None
        current_event = None
        current_data = None

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                # 空行表示一个事件结束，处理当前事件
                if current_event == "message" and current_data:
                    try:
                        data = json.loads(current_data)
                        # 检查是否是 CommonJudgeResponse 格式
                        if isinstance(data, dict) and "conversationId" in data:
                            final_response = data
                    except json.JSONDecodeError:
                        pass
                current_event = None
                current_data = None
                continue

            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                current_data = line[6:].strip()
                if current_data == "[DONE]":
                    break
                elif current_data == "[FLUSH]":
                    continue
                elif current_event == "message" and current_data:
                    try:
                        data = json.loads(current_data)
                        # 检查是否是 CommonJudgeResponse 格式
                        if isinstance(data, dict) and "conversationId" in data:
                            final_response = data
                    except json.JSONDecodeError:
                        pass

        if final_response is None:
            logging.error("未能从 SSE 响应中提取最终响应")
            return None

        # 从最终响应中提取 score 并计算 is_correct
        # CommonJudgeResponse 格式: {"message": {"content": "..."}, ...}
        message = final_response.get("message", {})
        content = message.get("content", "")

        # 从 content 中解析得分
        # 使用正则表达式提取得分
        score = None
        patterns = [
            r"\*\*得分：\*\*\s*([0-9.]+)",
            r"得分：\*\*\s*([0-9.]+)",
            r"\*\*得分：\s*([0-9.]+)",
            r"得分：\s*([0-9.]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    score = float(match.group(1))
                    if score > 1.0:
                        score = min(score / 100.0, 1.0)
                    break
                except ValueError:
                    continue

        if score is None:
            logging.warning(f"未能从响应中解析得分: {content[:200]}")
            return None

        # 计算 is_correct: score >= 1.0 为 True，否则为 False
        is_correct = score >= 1.0

        logging.info(f"主观题判题结果: score={score}, is_correct={is_correct}")
        return {"is_correct": is_correct, "score": score, "content": content}

    except requests.exceptions.Timeout:
        logging.error(f"主观题判题 SSE 接口请求超时: {api_url}")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"主观题判题 SSE 接口请求失败: {e}")
        return None
    except Exception as e:
        logging.error(f"主观题判题 SSE 接口处理异常: {e}", exc_info=True)
        return None


def count_non_empty_lines(file_path: Path) -> int:
    """
    统计文件中的非空行数

    Args:
        file_path: 文件路径

    Returns:
        非空行数
    """
    count = 0
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
    except Exception:
        pass
    return count


def process_single_sample(
    line_num: int,
    sample: Dict[str, Any],
    api_url: str,
    timeout: int,
    headers: Dict[str, str],
    judge_config: Optional[Dict[str, Any]],
    settings_config: Dict[str, Any],
    logger: logging.Logger,
    subjective_judge_config: Optional[Dict[str, Any]] = None,
) -> Tuple[int, Dict[str, Any], bool]:
    """
    处理单个样本

    Args:
        line_num: 行号
        sample: 样本数据
        api_url: API 地址
        timeout: 超时时间
        headers: 请求头
        judge_config: 判题配置
        settings_config: 设置配置
        logger: 日志记录器
        subjective_judge_config: 主观题判题配置（用于 topic_type == 4）

    Returns:
        (line_num, processed_sample, is_success) 元组
    """
    try:
        # 转换为 API 输入格式
        api_input = convert_to_api_input(sample)
        if api_input is None:
            logger.warning(f"第 {line_num} 行转换失败，跳过")
            # 仍然保存原始数据，但标记为失败
            sample["infer_results"] = {
                "error": "转换失败",
                "total_cost_time_ms": None,
                "recog_results": {"stu_answers": [], "raw_result": ""},
            }
            return (line_num, sample, False)

        # 获取 topic_type
        topic_id = api_input["question_info"]["topic_info"]["topic_id"]
        topic_type = api_input["question_info"]["topic_info"].get("topic_type")
        logger.info(
            f"处理第 {line_num} 行，topic_id: {topic_id}, topic_type: {topic_type}"
        )

        # 检查是否是 topic_type == 4（主观题）
        #if topic_type == 4:
        if topic_type not in [1,2,3]:
            # 调用主观题判题接口
            if subjective_judge_config is None:
                logger.error(
                    f"第 {line_num} 行 topic_type=4 但未配置 subjective_judge，跳过"
                )
                sample["infer_results"] = {
                    "error": "topic_type=4 但未配置 subjective_judge",
                    "total_cost_time_ms": None,
                    "recog_results": {"stu_answers": [], "raw_result": ""},
                }
                return (line_num, sample, False)

            subjective_base_url = subjective_judge_config.get("base_url")
            subjective_endpoint = subjective_judge_config.get(
                "endpoint", "/judge/streaming/subjective"
            )
            subjective_api_url = f"{subjective_base_url}{subjective_endpoint}"
            subjective_timeout = subjective_judge_config.get("timeout", 60)

            logger.info(f"调用主观题判题接口，topic_id: {topic_id}")
            subjective_start_time = time.time()

            max_retries = settings_config.get("max_retries", 3)
            retry_delay = settings_config.get("retry_delay", 1)
            subjective_result = None

            for attempt in range(max_retries):
                subjective_result = call_subjective_judge_sse(
                    subjective_api_url, api_input, subjective_timeout, headers
                )
                if subjective_result is not None:
                    break
                if attempt < max_retries - 1:
                    logger.warning(
                        f"第 {line_num} 行主观题判题接口调用失败，{retry_delay} 秒后重试..."
                    )
                    time.sleep(retry_delay)

            subjective_end_time = time.time()
            subjective_cost_time_ms = int(
                (subjective_end_time - subjective_start_time) * 1000
            )

            if subjective_result is None:
                logger.error(f"第 {line_num} 行主观题判题接口调用最终失败")
                sample["infer_results"] = {
                    "error": "主观题判题接口调用失败",
                    "total_cost_time_ms": subjective_cost_time_ms,
                    "recog_results": {"stu_answers": [], "raw_result": ""},
                }
                return (line_num, sample, False)

            # 提取 is_correct
            is_correct = subjective_result.get("is_correct")

            # 保存结果
            infer_results = {
                "total_cost_time_ms": subjective_cost_time_ms,
                "recog_results": {
                    "stu_answers": [],
                    "raw_result": subjective_result.get("content", ""),
                },
            }
            if is_correct is not None:
                infer_results["is_correct"] = is_correct

            sample["infer_results"] = infer_results
            logger.info(f"第 {line_num} 行处理成功，is_correct={is_correct}")
            return (line_num, sample, True)

        # 继续原有的客观题处理流程

        max_retries = settings_config.get("max_retries", 3)
        retry_delay = settings_config.get("retry_delay", 1)
        api_response = None

        # 记录空白识别耗时
        blank_recog_start_time = time.time()
        for attempt in range(max_retries):
            api_response = call_api(api_url, api_input, timeout, headers)
            if api_response is not None:
                break
            if attempt < max_retries - 1:
                logger.warning(
                    f"第 {line_num} 行 API 调用失败，{retry_delay} 秒后重试..."
                )
                time.sleep(retry_delay)
        blank_recog_end_time = time.time()
        blank_recog_cost_time_ms = int(
            (blank_recog_end_time - blank_recog_start_time) * 1000
        )

        if api_response is None:
            logger.error(f"第 {line_num} 行 API 调用最终失败")
            # 保存失败结果
            sample["infer_results"] = {
                "error": "API 调用失败",
                "total_cost_time_ms": blank_recog_cost_time_ms,
                "recog_results": {"stu_answers": [], "raw_result": ""},
            }
            return (line_num, sample, False)

        # 检查 status_code（/judge/objective 接口返回格式）
        status_code = api_response.get("status_code", 0)
        if status_code != 0 and status_code != 200:
            error_message = api_response.get("message", "API 返回错误状态码")
            logger.error(
                f"第 {line_num} 行 API 返回错误: status_code={status_code}, message={error_message}"
            )
            # 保存失败结果
            sample["infer_results"] = {
                "error": f"API 返回错误: status_code={status_code}, message={error_message}",
                "total_cost_time_ms": blank_recog_cost_time_ms,
                "recog_results": {"stu_answers": [], "raw_result": ""},
            }
            return (line_num, sample, False)

        # 提取识别结果
        recog_results = api_response.get("recog_results", {})
        if isinstance(recog_results, list):
            # 如果返回的是列表（错误情况），转换为空结果
            recog_results = {"stu_answers": [], "raw_result": ""}
        elif not isinstance(recog_results, dict):
            recog_results = {"stu_answers": [], "raw_result": ""}

        # 确保 recog_results 包含必要字段
        if "stu_answers" not in recog_results:
            recog_results["stu_answers"] = []
        if "raw_result" not in recog_results:
            recog_results["raw_result"] = ""

        # 调用判题接口
        is_correct = None
        judge_cost_time_ms = None
        if judge_config:
            judge_base_url = judge_config.get("base_url")
            judge_endpoint = judge_config.get("endpoint", "/api/cms/judge")
            if not judge_base_url:
                logger.warning("判题接口未配置 base_url，跳过判题")
            else:
                judge_url = f"{judge_base_url}{judge_endpoint}"
                judge_timeout = judge_config.get("timeout", 60)
                judge_salt = judge_config.get("salt", "llm-router")
                topic_id = api_input["question_info"]["topic_info"]["topic_id"]

                logger.info(f"调用判题接口，topic_id: {topic_id}")
                # 记录判题耗时
                judge_start_time = time.time()
                judge_response = call_judge_api(
                    judge_url, topic_id, recog_results, judge_timeout, judge_salt
                )
                judge_end_time = time.time()
                judge_cost_time_ms = int((judge_end_time - judge_start_time) * 1000)

                if judge_response:
                    # 解析判题结果
                    try:
                        data = judge_response.get("data", {})
                        result = data.get("result", {})
                        judge_value = result.get("judge")
                        # judge: 1 表示正确，0 表示错误
                        is_correct = (
                            (judge_value == 1) if judge_value is not None else None
                        )
                        logger.info(
                            f"判题结果: judge={judge_value}, is_correct={is_correct}"
                        )
                    except Exception as e:
                        logger.warning(f"解析判题结果失败: {e}")
                else:
                    logger.warning("判题接口调用失败")
        else:
            logger.info("未配置判题接口，跳过判题")

        # 保存结果
        # 计算总时长
        total_cost_time_ms = None
        if blank_recog_cost_time_ms is not None or judge_cost_time_ms is not None:
            total_cost_time_ms = (blank_recog_cost_time_ms or 0) + (judge_cost_time_ms or 0)
        
        infer_results = {
            "total_cost_time_ms": total_cost_time_ms,
            "recog_results": recog_results,
        }
        if is_correct is not None:
            infer_results["is_correct"] = is_correct

        sample["infer_results"] = infer_results

        logger.info(f"第 {line_num} 行处理成功")
        return (line_num, sample, True)

    except json.JSONDecodeError as e:
        logger.error(f"第 {line_num} 行 JSON 解析失败: {e}")
        sample["infer_results"] = {
            "error": f"JSON 解析失败: {e}",
            "total_cost_time_ms": None,
            "recog_results": {"stu_answers": [], "raw_result": ""},
        }
        return (line_num, sample, False)
    except Exception as e:
        logger.error(f"第 {line_num} 行处理异常: {e}", exc_info=True)
        sample["infer_results"] = {
            "error": f"处理异常: {e}",
            "total_cost_time_ms": None,
            "recog_results": {"stu_answers": [], "raw_result": ""},
        }
        return (line_num, sample, False)


def load_existing_results(
    output_file: Path, logger: logging.Logger
) -> Dict[int, Dict[str, Any]]:
    """
    加载已有的结果文件，返回成功 case 的索引

    Args:
        output_file: 输出文件路径
        logger: 日志记录器

    Returns:
        字典，key 为行号（从1开始），value 为完整的样本数据
    """
    existing_results = {}
    if not output_file.exists():
        logger.info(f"输出文件不存在: {output_file}，将从头开始处理")
        return existing_results

    logger.info(f"读取已有结果文件: {output_file}")
    success_count = 0
    failed_count = 0

    try:
        with open(output_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    sample = json.loads(line)
                    infer_results = sample.get("infer_results", {})

                    # 检查是否有 error 字段
                    if "error" in infer_results:
                        failed_count += 1
                        continue  # 跳过失败的 case，需要重新处理

                    # 使用行号作为 key
                    existing_results[line_num] = sample
                    success_count += 1
                except json.JSONDecodeError as e:
                    logger.warning(f"解析已有结果文件第 {line_num} 行失败: {e}")
                    continue
    except Exception as e:
        logger.warning(f"读取已有结果文件失败: {e}，将从头开始处理")
        return {}

    logger.info(
        f"从已有结果文件中加载: 成功 {success_count} 个，失败 {failed_count} 个（将重新处理）"
    )
    return existing_results


def process_samples(config: Dict[str, Any], logger: logging.Logger):
    """处理所有测试样例"""
    # 加载配置 - 必须使用 objective_judge 配置
    objective_judge_config = config.get("objective_judge")
    if objective_judge_config is None:
        logger.error("配置文件中缺少 objective_judge 配置")
        sys.exit(1)

    judge_config = config.get("judge")
    data_config = config["data"]
    settings_config = config["settings"]

    base_url = objective_judge_config["base_url"]
    # 如果配置中没有 endpoint，默认使用 /judge/objective
    endpoint = objective_judge_config.get("endpoint", "/judge/objective")
    api_url = f"{base_url}{endpoint}"
    timeout = objective_judge_config.get("timeout", 60)

    logger.info(f"API 地址: {api_url}")

    # 处理路径：输入文件相对于项目根目录，输出文件相对于工作区根目录
    input_file_path = data_config["input_file"]
    input_file = Path(input_file_path)

    output_file_path = data_config["output_file"]
    if not os.path.isabs(output_file_path):
        output_file = WORKSPACE_DIR / output_file_path
    else:
        output_file = Path(output_file_path)

    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # 从配置读取测试模式设置
    test_count = settings_config.get("test_count", 0)
    test_mode = test_count > 0

    # 测试模式：修改输出文件名
    if test_mode:
        output_file = output_file.parent / f"test_{output_file.name}"
        logger.info(f"测试模式：只处理前 {test_count} 个样例")
        logger.info(f"测试结果将保存到: {output_file}")

    # 检查是否启用重跑失败 case 模式（测试模式下不生效）
    retry_failed = settings_config.get("retry_failed", False)
    if test_mode and retry_failed:
        logger.info("测试模式下，retry_failed 不生效，将从头开始处理")
        retry_failed = False

    existing_results = {}
    if retry_failed:
        # 检查输入文件和输出文件的行数是否相等（仅在非测试模式下检查）
        # 在测试模式下，输出文件可能只包含部分数据，所以不检查行数
        if output_file.exists():
            input_line_count = count_non_empty_lines(input_file)
            output_line_count = count_non_empty_lines(output_file)

            if input_line_count != output_line_count:
                logger.error("=" * 60)
                logger.error("错误：输入文件和输出文件的行数不相等！")
                logger.error(f"输入文件 ({input_file}): {input_line_count} 行")
                logger.error(f"输出文件 ({output_file}): {output_line_count} 行")
                logger.error("=" * 60)
                logger.error("重跑失败模式要求输入文件和输出文件的行数必须相等，")
                logger.error("这样才能通过行号匹配已有结果。")
                logger.error("请检查文件是否匹配，或删除输出文件从头开始处理。")
                logger.error("=" * 60)
                sys.exit(1)

        existing_results = load_existing_results(output_file, logger)
        logger.info(f"重跑失败模式已启用，已加载 {len(existing_results)} 个成功的结果")

    # 设置请求头
    headers = {"Content-Type": "application/json"}

    # 获取 batch_size 配置，用于控制并发数
    batch_size = data_config.get("batch_size", 1)
    if batch_size < 1:
        batch_size = 1
        logger.warning(f"batch_size 配置无效，使用默认值 1")

    logger.info(f"并发处理配置: batch_size={batch_size}")

    # 统计信息
    total_count = 0
    success_count = 0
    fail_count = 0
    skipped_count = 0  # 跳过的已成功 case 数量
    start_time = time.time()

    # 读取并处理每一行
    logger.info(f"开始处理文件: {input_file}")

    # 如果启用重跑失败模式且输出文件已存在，创建备份并创建新文件
    if retry_failed and output_file.exists():
        backup_file = (
            output_file.parent
            / f"{output_file.stem}_backup_{int(time.time())}{output_file.suffix}"
        )
        logger.info(f"备份已有结果文件到: {backup_file}")
        shutil.copy2(output_file, backup_file)

    # 读取所有需要处理的样本
    samples_to_process = []
    with open(input_file, "r", encoding="utf-8") as infile:
        for line_num, line in enumerate(infile, 1):
            line = line.strip()
            if not line:
                continue

            # 测试模式：只处理指定数量的样例
            if test_mode and total_count >= test_count:
                logger.info(f"测试模式：已读取 {test_count} 个样例，停止读取")
                break

            total_count += 1

            try:
                # 解析 JSON
                sample = json.loads(line)

                # 检查是否已经成功处理过（重跑失败模式）
                if retry_failed and line_num in existing_results:
                    # 使用已有结果，不需要处理
                    skipped_count += 1
                    continue

                samples_to_process.append((line_num, sample))

            except json.JSONDecodeError as e:
                logger.error(f"第 {line_num} 行 JSON 解析失败: {e}")
                # 创建失败结果
                fail_sample = {
                    "infer_results": {
                        "error": f"JSON 解析失败: {e}",
                        "total_cost_time_ms": None,
                        "recog_results": {"stu_answers": [], "raw_result": ""},
                    }
                }
                samples_to_process.append((line_num, fail_sample))

    logger.info(
        f"共读取 {total_count} 个样本，需要处理 {len(samples_to_process)} 个（跳过 {skipped_count} 个已成功的）"
    )

    # 使用线程池并发处理
    results_dict = {}  # 存储处理结果，key 为 line_num
    stats_lock = Lock()  # 用于保护统计信息的锁

    # 创建行号到原始样本的映射，用于异常处理时保留原始数据
    line_num_to_original_sample = {
        line_num: sample for line_num, sample in samples_to_process
    }

    # 获取 subjective_judge 配置
    subjective_judge_config = config.get("subjective_judge")

    def process_with_stats(line_num, sample):
        """处理单个样本并更新统计信息"""
        result = process_single_sample(
            line_num,
            sample,
            api_url,
            timeout,
            headers,
            judge_config,
            settings_config,
            logger,
            subjective_judge_config,
        )
        line_num_result, processed_sample, is_success = result

        # 更新统计信息（线程安全）
        with stats_lock:
            nonlocal success_count, fail_count
            if is_success:
                success_count += 1
            else:
                fail_count += 1

        return result

    # 使用 ThreadPoolExecutor 并发处理
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        # 提交所有任务
        future_to_line_num = {
            executor.submit(process_with_stats, line_num, sample): line_num
            for line_num, sample in samples_to_process
        }

        # 收集结果
        completed = 0
        save_interval = settings_config.get("save_interval", 10)

        for future in as_completed(future_to_line_num):
            try:
                line_num_result, processed_sample, is_success = future.result()
                results_dict[line_num_result] = processed_sample
                completed += 1

                # 定期输出进度
                if completed % save_interval == 0:
                    with stats_lock:
                        logger.info(
                            f"已处理 {completed}/{len(samples_to_process)} 个样本，成功: {success_count}, 失败: {fail_count}"
                        )
            except Exception as e:
                line_num = future_to_line_num[future]
                logger.error(f"第 {line_num} 行处理异常: {e}", exc_info=True)
                # 获取原始样本数据，保留完整结构
                original_sample = line_num_to_original_sample.get(line_num, {})
                # 创建失败结果，但保留原始样本的所有字段
                fail_sample = (
                    original_sample.copy() if isinstance(original_sample, dict) else {}
                )
                fail_sample["infer_results"] = {
                    "error": f"处理异常: {e}",
                    "total_cost_time_ms": None,
                    "recog_results": {"stu_answers": [], "raw_result": ""},
                }
                results_dict[line_num] = fail_sample
                with stats_lock:
                    fail_count += 1

        # 检查是否所有任务都完成了
        # 使用 results_dict 的长度来检查，因为所有完成的任务（成功或失败）都应该在 results_dict 中
        if len(results_dict) < len(samples_to_process):
            missing_count = len(samples_to_process) - len(results_dict)
            logger.warning(
                f"警告: 有 {missing_count} 个任务的结果未被收集，将为它们创建失败结果"
            )
            # 为缺失的任务创建失败结果
            for line_num, sample in samples_to_process:
                if line_num not in results_dict:
                    logger.warning(f"第 {line_num} 行结果缺失，创建失败结果")
                    original_sample = line_num_to_original_sample.get(line_num, {})
                    fail_sample = (
                        original_sample.copy()
                        if isinstance(original_sample, dict)
                        else {}
                    )
                    fail_sample["infer_results"] = {
                        "error": "任务结果未被收集（可能超时或异常）",
                        "total_cost_time_ms": None,
                        "recog_results": {"stu_answers": [], "raw_result": ""},
                    }
                    results_dict[line_num] = fail_sample
                    # 更新失败计数（此时线程池已关闭，不需要锁）
                    fail_count += 1

    # 按行号顺序写入结果
    logger.info("开始写入结果文件...")
    with open(output_file, "w", encoding="utf-8") as outfile:
        # 合并所有结果（包括跳过的和处理过的）
        all_results = {}

        # 添加已跳过的结果（重跑失败模式）
        if retry_failed:
            all_results.update(existing_results)

        # 添加处理结果（会覆盖已跳过的结果，如果有重复）
        all_results.update(results_dict)

        # 按行号顺序写入所有结果
        for line_num in sorted(all_results.keys()):
            sample = all_results[line_num]
            outfile.write(json.dumps(sample, ensure_ascii=False) + "\n")

        outfile.flush()

    logger.info("结果文件写入完成")

    # 输出统计信息
    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info("处理完成！")
    if test_mode:
        logger.info(f"[测试模式] 处理了 {total_count} 个样本（限制: {test_count}）")
    else:
        logger.info(f"总样本数: {total_count}")
    if retry_failed and skipped_count > 0:
        logger.info(f"跳过（已成功）: {skipped_count}")
    logger.info(f"成功: {success_count}")
    logger.info(f"失败: {fail_count}")
    logger.info(f"总耗时: {elapsed_time:.2f} 秒")
    processed_count = total_count - skipped_count
    if processed_count > 0:
        logger.info(
            f"平均耗时: {elapsed_time/processed_count:.2f} 秒/样本（仅计算实际处理的样本）"
        )
    logger.info(f"结果已保存到: {output_file}")
    logger.info("=" * 60)


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="推理脚本：从 JSONL 文件读取测试样例，调用 /judge/objective 接口，保存推理结果"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="配置文件路径（默认: config.yaml）",
    )
    args = parser.parse_args()

    # 获取配置文件路径
    config_path_str = args.config
    if os.path.isabs(config_path_str):
        config_path = Path(config_path_str)
    else:
        config_path = WORKSPACE_DIR / config_path_str

    if not config_path.exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    # 加载配置
    config = load_config(str(config_path))

    # 设置日志
    log_config = config.get("logging", {})
    log_level = log_config.get("level", "INFO")
    log_file_path = log_config.get("log_file", "results/infer.log")
    if not os.path.isabs(log_file_path):
        log_file = str(WORKSPACE_DIR / log_file_path)
    else:
        log_file = log_file_path
    logger = setup_logging(log_level, log_file)

    # 检查测试模式配置
    test_count = config.get("settings", {}).get("test_count", 0)

    logger.info("=" * 60)
    logger.info("推理脚本启动")
    logger.info(f"配置文件: {config_path}")
    if test_count > 0:
        logger.info(f"测试模式: 只处理前 {test_count} 个样例")
    logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # 处理样本
    try:
        process_samples(config, logger)
    except KeyboardInterrupt:
        logger.warning("用户中断处理")
        sys.exit(1)
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
